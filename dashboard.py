from database import get_db, init_db
from models import Appointment, Customer

init_db()

def view_all_bookings():
    db = get_db()
    
    appointments = db.query(Appointment).all()
    
    print("\n" + "="*80)
    print("🍎 APPLEFIXIT - ALL BOOKINGS")
    print("="*80 + "\n")
    
    if not appointments:
        print("❌ No bookings found\n")
        return
    
    for appt in appointments:
        customer = appt.customer
        print(f"📋 Confirmation: AFX-{appt.id:05d}")
        print(f"👤 Customer: {customer.name}")
        print(f"📱 Phone: {customer.phone}")
        print(f"🍎 Device: {appt.device_type}")
        print(f"🔧 Issue: {appt.issue_description}")
        print(f"⏰ Time: {appt.time_slot}")
        print(f"📅 Status: {appt.status}")
        print(f"📍 Booked: {appt.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80 + "\n")
    
    total = len(appointments)
    print(f"Total Bookings: {total}")
    print("="*80 + "\n")

if __name__ == '__main__':
    view_all_bookings()
