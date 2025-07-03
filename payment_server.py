# payment_server.py - שרת תשלומים עצמאי

from flask import Flask, render_template_string, request, jsonify
import requests
import json
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

# טוען משתני סביבה
load_dotenv()

app = Flask(__name__)

# הגדרות מקובץ .env או ברירות מחדל
GREEN_API_URL = os.getenv("GREEN_API_URL")
ID_INSTANCE = os.getenv("GREEN_API_ID_INSTANCE")
API_TOKEN_INSTANCE = os.getenv("GREEN_API_TOKEN_INSTANCE")
API_BASE_URL = os.getenv("BASE44_API_BASE_URL")
API_KEY = os.getenv("BASE44_API_KEY")
APP_ID = os.getenv("BASE44_APP_ID")
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", os.getenv("PAYMENT_SERVER_PORT", 8000)))

# אחסון תשלומים ממתינים
pending_payments = {}

# תבנית HTML לדף התשלום
PAYMENT_PAGE_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>תשלום - פיצריית גל</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .payment-container {
            background: white;
            border-radius: 20px;
            padding: 40px 30px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            max-width: 450px;
            width: 100%;
            text-align: center;
            animation: slideUp 0.6s ease-out;
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .pizza-icon {
            font-size: 4.5em;
            margin-bottom: 20px;
            animation: bounce 2s infinite;
        }
        
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {
                transform: translateY(0);
            }
            40% {
                transform: translateY(-10px);
            }
            60% {
                transform: translateY(-5px);
            }
        }
        
        h1 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-weight: 600;
        }
        
        .order-details {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            padding: 25px;
            margin: 25px 0;
            text-align: right;
            border: 2px solid #dee2e6;
        }
        
        .order-details h3 {
            color: #495057;
            margin-bottom: 15px;
            text-align: center;
            font-size: 1.2em;
        }
        
        .order-details p {
            margin: 8px 0;
            color: #6c757d;
            font-size: 1em;
        }
        
        .order-details strong {
            color: #495057;
        }
        
        .amount {
            font-size: 2.5em;
            color: #e74c3c;
            font-weight: bold;
            margin: 25px 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        
        .pay-button {
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            color: white;
            border: none;
            padding: 18px 35px;
            font-size: 1.3em;
            border-radius: 12px;
            cursor: pointer;
            width: 100%;
            margin: 15px 0;
            transition: all 0.3s ease;
            font-weight: 600;
            box-shadow: 0 8px 15px rgba(39, 174, 96, 0.3);
        }
        
        .pay-button:hover {
            background: linear-gradient(135deg, #219a52 0%, #27ae60 100%);
            transform: translateY(-3px);
            box-shadow: 0 12px 20px rgba(39, 174, 96, 0.4);
        }
        
        .pay-button:active {
            transform: translateY(-1px);
        }
        
        .pay-button:disabled {
            background: #95a5a6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .success {
            color: #27ae60;
            font-weight: bold;
            margin-top: 25px;
            padding: 20px;
            background: #d4edda;
            border-radius: 10px;
            border: 2px solid #c3e6cb;
        }
        
        .loading {
            display: none;
            margin: 25px 0;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .note {
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .security-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            color: #28a745;
            font-size: 0.8em;
            margin-top: 10px;
        }
        
        @media (max-width: 480px) {
            .payment-container {
                padding: 30px 20px;
                margin: 10px;
            }
            
            .amount {
                font-size: 2em;
            }
            
            .pay-button {
                font-size: 1.1em;
                padding: 15px 25px;
            }
        }
    </style>
</head>
<body>
    <div class="payment-container">
        <div class="pizza-icon">🍕</div>
        <h1>תשלום מאובטח</h1>
        
        <div class="order-details">
            <h3>📋 פרטי ההזמנה</h3>
            <p><strong>מספר הזמנה:</strong> #{{ order_number }}</p>
            <p><strong>שם הלקוח:</strong> {{ customer_name }}</p>
            <p><strong>כתובת משלוח:</strong> {{ address }}, {{ city }}</p>
            <p><strong>תאריך:</strong> {{ order_date }}</p>
        </div>
        
        <div class="amount">{{ amount }} ₪</div>
        
        <div id="payment-section">
            <button class="pay-button" onclick="processPayment()">
                💳 אישור תשלום מאובטח
            </button>
            <div class="security-badge">
                🔒 תשלום מאובטח ומוצפן
            </div>
            <div class="note">
                זוהי מערכת דמו לבדיקות<br>
                התשלום יאושר מיידית
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p><strong>מעבד תשלום...</strong></p>
            <p>אנא המתן, התשלום נמצא בעיבוד</p>
        </div>
        
        <div id="success-message" style="display: none;">
            <div class="success">
                <div style="font-size: 3em; margin-bottom: 15px;">✅</div>
                <strong>התשלום אושר בהצלחה!</strong><br><br>
                🍕 ההזמנה שלך אושרה ונשלחת להכנה<br>
                ⏰ זמן הכנה משוער: 20-30 דקות<br><br>
                תודה שבחרת בנו! ❤️
            </div>
        </div>
    </div>

    <script>
        function processPayment() {
            // הסתר כפתור התשלום והצג טוען
            document.getElementById('payment-section').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            
            // סימולציה של זמן עיבוד תשלום
            setTimeout(() => {
                fetch('/confirm_payment/{{ payment_id }}', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        timestamp: new Date().toISOString(),
                        payment_method: 'demo'
                    })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    if (data.success) {
                        document.getElementById('success-message').style.display = 'block';
                        
                        // הודעה נוספת אחרי 3 שניות
                        setTimeout(() => {
                            alert('תוכל לסגור את הדף. תקבל עדכונים בוואטסאפ 📱');
                        }, 3000);
                    } else {
                        alert('שגיאה בתשלום: ' + (data.error || 'אנא נסה שוב'));
                        document.getElementById('payment-section').style.display = 'block';
                    }
                })
                .catch(error => {
                    console.error('Payment error:', error);
                    document.getElementById('loading').style.display = 'none';
                    alert('שגיאה בחיבור. אנא בדוק את החיבור לאינטרנט ונסה שוב.');
                    document.getElementById('payment-section').style.display = 'block';
                });
            }, 2500); // סימולציה של 2.5 שניות עיבוד
        }
        
        // אפקט ויזואלי נוסף
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Payment page loaded for order #{{ order_number }}');
        });
    </script>
</body>
</html>
"""

def send_whatsapp_message(chat_id, message):
    """שליחת הודעה בוואטסאפ"""
    if not all([GREEN_API_URL, ID_INSTANCE, API_TOKEN_INSTANCE]):
        print("⚠️ WhatsApp credentials not configured")
        return None
        
    url = f"{GREEN_API_URL}/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"
    
    payload = {
        "chatId": chat_id,
        "message": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        print(f"✅ WhatsApp message sent to {chat_id}")
        return response.json()
    except Exception as e:
        print(f"❌ Error sending WhatsApp message: {e}")
        return None

def make_api_request(api_path, method='GET', data=None):
    """קריאות API למערכת הזמנות"""
    if not all([API_BASE_URL, API_KEY]):
        print("⚠️ API credentials not configured")
        return None
        
    url = f'{API_BASE_URL}/{api_path}'
    headers = {
        'api_key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        if method.upper() == 'GET':
            response = requests.request(method, url, headers=headers, params=data)
        else:
            response = requests.request(method, url, headers=headers, json=data)
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        return None

def get_all_orders():
    """קבלת כל ההזמנות"""
    if not APP_ID:
        print("⚠️ APP_ID not configured")
        return []
        
    orders = make_api_request(f'apps/{APP_ID}/entities/Order')
    return orders if orders else []

@app.route('/')
def home():
    """דף בית - מידע על השרת"""
    return f"""
    <html dir="rtl">
    <head>
        <title>שרת תשלומים</title>
        <style>
            body {{ font-family: Arial; padding: 20px; text-align: center; }}
            .status {{ color: green; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>🍕 שרת תשלומים פעיל</h1>
        <p class="status">✅ השרת פועל תקין</p>
        <p>📊 תשלומים ממתינים: {len(pending_payments)}</p>
        <p>🕐 זמן: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        <hr>
        <p>API Endpoints:</p>
        <ul style="text-align: left; max-width: 400px; margin: 0 auto;">
            <li>POST /create_payment - יצירת תשלום חדש</li>
            <li>GET /payment/&lt;id&gt; - דף תשלום</li>
            <li>POST /confirm_payment/&lt;id&gt; - אישור תשלום</li>
            <li>GET /health - בדיקת בריאות</li>
        </ul>
    </body>
    </html>
    """

@app.route('/payment/<payment_id>')
def payment_page(payment_id):
    """דף התשלום"""
    if payment_id not in pending_payments:
        return f"""
        <html dir="rtl">
        <head><title>שגיאה</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>❌ קישור תשלום לא תקין</h1>
            <p>הקישור פג תוקף או שאינו קיים</p>
            <p>אנא צור קשר עם המסעדה</p>
        </body>
        </html>
        """, 404
    
    payment_data = pending_payments[payment_id]
    
    # הוספת תאריך יפה
    order_date = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    return render_template_string(
        PAYMENT_PAGE_HTML,
        payment_id=payment_id,
        order_number=payment_data['order_number'],
        customer_name=payment_data['customer_name'],
        address=payment_data['address'],
        city=payment_data['city'],
        amount=payment_data['amount'],
        order_date=order_date
    )

@app.route('/confirm_payment/<payment_id>', methods=['POST'])
def confirm_payment(payment_id):
    """אישור תשלום ועדכון סטטוס הזמנה"""
    if payment_id not in pending_payments:
        return jsonify({'success': False, 'error': 'מזהה תשלום לא תקין'})
    
    payment_data = pending_payments[payment_id]
    
    try:
        order_number = payment_data['order_number']
        chat_id = payment_data['chat_id']
        
        print(f"💳 מעבד תשלום עבור הזמנה #{order_number}")
        
        # חיפוש ההזמנה במערכת
        orders = get_all_orders()
        target_order = None
        
        for order in orders:
            if order.get('orderNumber') == order_number:
                target_order = order
                break
        
        if not target_order:
            print(f"❌ הזמנה #{order_number} לא נמצאה")
            return jsonify({'success': False, 'error': 'הזמנה לא נמצאה במערכת'})
        
        current_status = target_order.get('status')
        print(f"🔍 הזמנה #{order_number}: סטטוס נוכחי = {current_status}")
        
        # עדכון סטטוס לפי המצב הנוכחי
        if current_status == "new":
            # מעבר מ-new ל-preparing + עדכון תשלום
            update_result = make_api_request(
                f'apps/{APP_ID}/entities/Order/{target_order["id"]}',
                method='PUT',
                data={
                    'status': 'preparing',
                    'paymentStatus': 'paid',
                    'paymentMethod': 'online_demo'
                }
            )
            
            if update_result:
               
                # הודעה למנהל (אם הוגדר)
                
                
                print(f"✅ תשלום אושר עבור הזמנה #{order_number}")
                del pending_payments[payment_id]
                return jsonify({'success': True, 'message': 'תשלום אושר בהצלחה'})
            else:
                print(f"❌ נכשל עדכון הזמנה #{order_number}")
                return jsonify({'success': False, 'error': 'נכשל עדכון ההזמנה במערכת'})
                
        elif current_status == "preparing":
            print(f"ℹ️ הזמנה #{order_number} כבר בהכנה")
            del pending_payments[payment_id]
            return jsonify({'success': True, 'message': 'התשלום כבר אושר קודם'})
            
        else:
            print(f"⚠️ הזמנה #{order_number} במצב לא צפוי: {current_status}")
            return jsonify({'success': False, 'error': f'הזמנה במצב {current_status}, לא ניתן לעבד תשלום'})
        
    except Exception as e:
        print(f"❌ שגיאה באישור תשלום: {e}")
        return jsonify({'success': False, 'error': f'שגיאה טכנית: {str(e)}'})

@app.route('/create_payment', methods=['POST'])
def create_payment():
    """יצירת תשלום חדש (API עבור הבוט)"""
    try:
        data = request.get_json()
        
        # בדיקת שדות חובה
        required_fields = ['order_number', 'customer_name', 'address', 'city', 'amount', 'chat_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'שדה חסר: {field}'})
        
        # יצירת מזהה תשלום ייחודי
        payment_id = str(uuid.uuid4())
        
        payment_data = {
            'order_number': data['order_number'],
            'customer_name': data['customer_name'],
            'address': data['address'],
            'city': data['city'],
            'amount': data['amount'],
            'chat_id': data['chat_id'],
            'created_at': datetime.now().isoformat()
        }
        
        # שמירת התשלום
        pending_payments[payment_id] = payment_data
        
        # יצירת קישור
        if SERVER_HOST == "localhost":
            payment_url = f"http://{SERVER_HOST}:{SERVER_PORT}/payment/{payment_id}"
        else:
            payment_url = f"https://{SERVER_HOST}/payment/{payment_id}"
        
        print(f"💳 נוצר קישור תשלום: {payment_url}")
        
        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'payment_url': payment_url,
            'order_number': data['order_number']
        })
        
    except Exception as e:
        print(f"❌ שגיאה ביצירת תשלום: {e}")
        return jsonify({'success': False, 'error': f'שגיאה ביצירת תשלום: {str(e)}'})

@app.route('/health')
def health_check():
    """בדיקת בריאות השרת"""
    return jsonify({
        'status': 'healthy',
        'pending_payments': len(pending_payments),
        'timestamp': datetime.now().isoformat(),
        'server_info': {
            'host': SERVER_HOST,
            'port': SERVER_PORT,
            'configured': {
                'whatsapp': bool(ID_INSTANCE and API_TOKEN_INSTANCE),
                'api': bool(API_KEY and APP_ID),
            }
        }
    })

@app.route('/admin/payments')
def admin_payments():
    """צפייה בתשלומים ממתינים (למנהל)"""
    if not pending_payments:
        return jsonify({'message': 'אין תשלומים ממתינים', 'payments': []})
    
    payments_list = []
    for payment_id, data in pending_payments.items():
        payments_list.append({
            'payment_id': payment_id,
            'order_number': data['order_number'],
            'customer_name': data['customer_name'],
            'amount': data['amount'],
            'created_at': data['created_at']
        })
    
    return jsonify({
        'count': len(payments_list),
        'payments': payments_list
    })

if __name__ == '__main__':
    print("🍕 מתחיל שרת תשלומים...")
    print(f"🌐 השרת יהיה זמין בכתובת: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"📊 בדיקת בריאות: http://{SERVER_HOST}:{SERVER_PORT}/health")
    print(f"🔧 מנהל תשלומים: http://{SERVER_HOST}:{SERVER_PORT}/admin/payments")
    
    # בדיקת הגדרות
    missing_configs = []
    if not ID_INSTANCE:
        missing_configs.append("GREEN_API_ID_INSTANCE")
    if not API_TOKEN_INSTANCE:
        missing_configs.append("GREEN_API_TOKEN_INSTANCE")
    if not API_KEY:
        missing_configs.append("BASE44_API_KEY")
    if not APP_ID:
        missing_configs.append("BASE44_APP_ID")
    
    if missing_configs:
        print(f"⚠️ הגדרות חסרות: {', '.join(missing_configs)}")
        print("💡 הוסף אותן לקובץ .env או כמשתני סביבה")
    else:
        print("✅ כל ההגדרות נטענו בהצלחה")
    
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False)