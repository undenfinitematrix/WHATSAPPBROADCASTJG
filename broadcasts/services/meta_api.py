"""
AeroChat Broadcasts Module — Meta API Service
================================================
Handles all direct communication with Meta's WhatsApp Cloud API:
- Fetching approved message templates
- Sending individual WhatsApp messages
- Template caching

Meta Cloud API docs:
  https://developers.facebook.com/docs/whatsapp/cloud-api

Usage:
    from broadcasts.services.meta_api import MetaAPIService
    meta = MetaAPIService()
    templates = await meta.get_approved_templates()
    result = await meta.send_message(phone, template_name, language, variables)
"""

import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx

from ..config import settings
from ..models import Template, TemplateComponent, TemplateButton, TemplateCategory

logger = logging.getLogger("broadcasts.meta_api")


class MetaAPIService:
    """
    Service for interacting with Meta's WhatsApp Cloud API.
    """

    # Class-level template cache (shared across instances)
    _template_cache: Optional[List[Template]] = None
    _cache_timestamp: Optional[datetime] = None
    _cache_expires_at: float = 0

    def __init__(self):
        self.base_url = f"{settings.META_API_BASE_URL}/{settings.META_API_VERSION}"
        self.phone_number_id = settings.META_PHONE_NUMBER_ID
        self.waba_id = settings.META_WABA_ID
        self.access_token = settings.META_ACCESS_TOKEN
        self.last_fetch_was_cached = False
        self.cache_timestamp = self.__class__._cache_timestamp

        # Reusable async HTTP client
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.DISPATCH_TIMEOUT),
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close the HTTP client. Call on shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # =========================================
    # Templates
    # =========================================

    async def get_approved_templates(self) -> List[Template]:
        """
        Fetch approved message templates from Meta.
        Returns cached results if within TTL.

        Meta API endpoint:
            GET /{waba_id}/message_templates?status=APPROVED

        Returns:
            List of Template models with parsed components.
        """
        # Check cache
        if self.__class__._template_cache and time.time() < self.__class__._cache_expires_at:
            self.last_fetch_was_cached = True
            self.cache_timestamp = self.__class__._cache_timestamp
            logger.debug("Returning cached templates")
            return self.__class__._template_cache

        self.last_fetch_was_cached = False
        logger.info("Fetching templates from Meta API")

        client = await self._get_client()
        templates: List[Template] = []
        url = f"{self.base_url}/{self.waba_id}/message_templates"
        params = {
            "status": "APPROVED",
            "limit": 100,
        }

        try:
            # Paginate through all templates
            while url:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                for tpl_data in data.get("data", []):
                    template = self._parse_template(tpl_data)
                    if template:
                        templates.append(template)

                # Handle pagination
                paging = data.get("paging", {})
                url = paging.get("next")
                params = {}  # Next URL includes params

            # Update cache
            self.__class__._template_cache = templates
            self.__class__._cache_timestamp = datetime.utcnow()
            self.__class__._cache_expires_at = time.time() + settings.TEMPLATE_CACHE_TTL
            self.cache_timestamp = self.__class__._cache_timestamp

            logger.info(f"Fetched {len(templates)} approved templates")
            return templates

        except httpx.HTTPStatusError as e:
            logger.error(f"Meta API error fetching templates: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"Meta API returned {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Network error fetching templates: {e}")
            raise RuntimeError(f"Failed to connect to Meta API: {str(e)}")

    def _parse_template(self, data: Dict[str, Any]) -> Optional[Template]:
        """
        Parse a raw template object from Meta's API into our Template model.

        Meta template structure:
        {
            "name": "hello_world",
            "language": "en_US",
            "status": "APPROVED",
            "category": "MARKETING",
            "id": "123456",
            "components": [
                {"type": "HEADER", "format": "IMAGE"},
                {"type": "BODY", "text": "Hello {{1}}!"},
                {"type": "FOOTER", "text": "Reply STOP to unsubscribe"},
                {"type": "BUTTONS", "buttons": [{"type": "URL", "text": "Shop", "url": "https://..."}]}
            ]
        }
        """
        try:
            components = []
            for comp_data in data.get("components", []):
                buttons = None
                if comp_data.get("buttons"):
                    buttons = [
                        TemplateButton(
                            type=btn.get("type", ""),
                            text=btn.get("text", ""),
                            url=btn.get("url"),
                            phone_number=btn.get("phone_number"),
                        )
                        for btn in comp_data["buttons"]
                    ]

                components.append(
                    TemplateComponent(
                        type=comp_data.get("type", ""),
                        format=comp_data.get("format"),
                        text=comp_data.get("text"),
                        buttons=buttons,
                    )
                )

            # Map Meta's category strings to our enum
            category_str = data.get("category", "MARKETING").upper()
            category_map = {
                "MARKETING": TemplateCategory.MARKETING,
                "UTILITY": TemplateCategory.UTILITY,
                "AUTHENTICATION": TemplateCategory.AUTHENTICATION,
            }
            category = category_map.get(category_str, TemplateCategory.MARKETING)

            return Template(
                id=data.get("id", ""),
                name=data.get("name", ""),
                language=data.get("language", "en"),
                category=category,
                status=data.get("status", "APPROVED"),
                components=components,
            )
        except Exception as e:
            logger.warning(f"Failed to parse template '{data.get('name', 'unknown')}': {e}")
            return None

    # =========================================
    # Sending Messages
    # =========================================

    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        language_code: str = "en",
        header_params: Optional[List[Dict[str, Any]]] = None,
        body_params: Optional[List[str]] = None,
        button_params: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a single template message via Meta's Messages API.

        Meta API endpoint:
            POST /{phone_number_id}/messages

        Args:
            to_phone: Recipient phone number in international format (e.g., "+6591234567")
            template_name: Name of the approved template
            language_code: Template language code (e.g., "en", "en_US")
            header_params: Header component parameters (for images, videos, etc.)
            body_params: Body text variable values (list of strings, positional)
            button_params: Button component parameters

        Returns:
            Meta API response dict with message ID:
            {"messaging_product": "whatsapp", "contacts": [...], "messages": [{"id": "wamid.xxx"}]}

        Raises:
            MessageSendError: If the send fails
        """
        client = await self._get_client()
        url = f"{self.base_url}/{self.phone_number_id}/messages"

        # Build the template components payload
        components = []

        # Header parameters (e.g., image URL)
        if header_params:
            components.append({
                "type": "header",
                "parameters": header_params,
            })

        # Body parameters (template variables {{1}}, {{2}}, etc.)
        if body_params:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": value} for value in body_params
                ],
            })

        # Button parameters
        if button_params:
            for i, btn_param in enumerate(button_params):
                components.append({
                    "type": "button",
                    "sub_type": btn_param.get("sub_type", "url"),
                    "index": str(i),
                    "parameters": btn_param.get("parameters", []),
                })

        payload = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(to_phone),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        # Only include components if there are parameters
        if components:
            payload["template"]["components"] = components

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            message_id = None
            messages = result.get("messages", [])
            if messages:
                message_id = messages[0].get("id")

            logger.debug(f"Message sent to {to_phone}: {message_id}")
            return result

        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass

            error_info = error_data.get("error", {})
            error_code = error_info.get("code", e.response.status_code)
            error_message = error_info.get("message", e.response.text)

            logger.error(f"Failed to send to {to_phone}: [{error_code}] {error_message}")
            raise MessageSendError(
                phone=to_phone,
                error_code=str(error_code),
                error_message=error_message,
            )
        except httpx.RequestError as e:
            logger.error(f"Network error sending to {to_phone}: {e}")
            raise MessageSendError(
                phone=to_phone,
                error_code="NETWORK_ERROR",
                error_message=str(e),
            )

    # =========================================
    # Phone Number Utilities
    # =========================================

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """
        Normalize a phone number to digits only (no +, spaces, dashes).
        Meta requires just digits, e.g., "6591234567" not "+65 9123 4567".
        """
        return "".join(c for c in phone if c.isdigit())

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """
        Basic validation for international phone numbers.
        Must be 7-15 digits after stripping non-numeric characters.
        """
        digits = "".join(c for c in phone if c.isdigit())
        return 7 <= len(digits) <= 15


class MessageSendError(Exception):
    """Raised when a message send fails."""

    def __init__(self, phone: str, error_code: str, error_message: str):
        self.phone = phone
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"Failed to send to {phone}: [{error_code}] {error_message}")
