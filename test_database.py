"""
Test Database Connection & Data Insertion
==========================================
Run this script to verify:
1. Database connection works
2. Tables are created
3. Data can be inserted and retrieved
"""

import asyncio
import sys
from datetime import datetime
import uuid

# Test database connection and operations
async def test_database():
    from broadcasts.config import settings
    from broadcasts.database import init_db, close_db, get_session, broadcasts_table, recipients_table
    from sqlalchemy import select, insert
    
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)
    
    try:
        # 1. Initialize database
        print("\n1️⃣  Initializing database...")
        await init_db()
        print("   ✅ Database initialized successfully!")
        
        # 2. Test connection
        print("\n2️⃣  Testing database connection...")
        print(f"   Database URL: {settings.DATABASE_URL}")
        
        async with get_session() as session:
            result = await session.execute(select(broadcasts_table))
            existing_broadcasts = result.fetchall()
            print(f"   ✅ Connected! Existing broadcasts: {len(existing_broadcasts)}")
        
        # 3. Insert test broadcast
        print("\n3️⃣  Inserting test broadcast...")
        async with get_session() as session:
            broadcast_id = str(uuid.uuid4())
            new_broadcast = insert(broadcasts_table).values(
                id=broadcast_id,
                campaign_name="Test Campaign",
                template_name="hello",
                template_language="en",
                status="draft",
                created_at=datetime.utcnow(),
                estimated_cost=0.01
            )
            await session.execute(new_broadcast)
            await session.commit()
            print("   ✅ Test broadcast inserted!")
            stored_broadcast_id = broadcast_id
        
        # 4. Retrieve test broadcast
        print("\n4️⃣  Retrieving test broadcast...")
        async with get_session() as session:
            result = await session.execute(
                select(broadcasts_table).where(broadcasts_table.c.campaign_name == "Test Campaign")
            )
            broadcast = result.fetchone()
            if broadcast:
                print(f"   ✅ Retrieved broadcast: {broadcast.campaign_name}")
                print(f"      - ID: {broadcast.id}")
                print(f"      - Status: {broadcast.status}")
                print(f"      - Created: {broadcast.created_at}")
            else:
                print("   ❌ Broadcast not found!")
                return False
        
        # 5. Test recipients table
        print("\n5️⃣  Inserting test recipient...")
        async with get_session() as session:
            recipient_id = str(uuid.uuid4())
            new_recipient = insert(recipients_table).values(
                id=recipient_id,
                broadcast_id=stored_broadcast_id,
                phone="1234567890",
                status="pending",
                created_at=datetime.utcnow()
            )
            await session.execute(new_recipient)
            await session.commit()
            print(f"   ✅ Test recipient inserted!")
        
        # 6. Verify recipient
        print("\n6️⃣  Retrieving recipients...")
        async with get_session() as session:
            result = await session.execute(
                select(recipients_table).where(recipients_table.c.phone == "1234567890")
            )
            recipients = result.fetchall()
            print(f"   ✅ Found {len(recipients)} recipient(s)")
            for recipient in recipients:
                print(f"      - Phone: {recipient.phone}, Status: {recipient.status}")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour database is working correctly!")
        print("You can now start the app with: uvicorn main:app --reload")
        
        # Cleanup
        await close_db()
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED!")
        print("=" * 60)
        print(f"\nError: {type(e).__name__}")
        print(f"Message: {str(e)}")
        
        if "access denied" in str(e).lower():
            print("\n💡 Connection hint:")
            print("   - Check your MySQL credentials in .env")
            print("   - Verify DATABASE_URL format: mysql+aiomysql://user:password@localhost:3306/aerochat")
            
        elif "database" in str(e).lower() and "does not exist" in str(e).lower():
            print("\n💡 Database hint:")
            print("   - Create the database manually:")
            print("   - Go to phpMyAdmin and create database 'aerochat'")
            print("   - Or run: mysql -u root -e 'CREATE DATABASE aerochat;'")
        
        await close_db()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database())
    sys.exit(0 if success else 1)
