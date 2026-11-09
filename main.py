import os
import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import google.generativeai as genai
import ezdxf

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def generate_dxf_layout(elements_data, filename="sketch.dxf"):
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()
    
    # رسم حدود الأرض العامة
    msp.add_lwpolyline([(0, 0), (20000, 0), (20000, 15000), (0, 15000), (0, 0)])

    # رسم العناصر الواردة بناءً على طلب المستخدم (المجلس، المستودع، البوفيه، إلخ)
    for item in elements_data.get("elements", []):
        name = item.get("name")
        x1, y1 = item.get("start", [0, 0])
        x2, y2 = item.get("end", [0, 0])
        msp.add_lwpolyline([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])
        msp.add_text(name, dxfattribs={'height': 300}).set_placement(((x1+x2)/2, (y1+y2)/2))

    doc.saveas(filename)
    return filename

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("جاري دراسة تفاصيل المخطط وتوليد ملف الكاد...")

    prompt = f"""
    أنت مهندس معماري محترف. حلل طلب الأرض والتوزيع التالي (المجلس بالشرق، المستودع بالشمال الغربي، البوفيه الملاصق للسور، المساحة بالوسط) وحوله إلى كائن JSON للإحداثيات بالمليمتر:
    الطلب: "{user_text}"
    أرجع كود JSON فقط بالشكل التالي:
    {{
      "elements": [
        {{"name": "المجلس (شرق)", "start": [12000, 0], "end": [20000, 10000]}},
        {{"name": "مستودع (شمال غرب)", "start": [0, 10000], "end": [4000, 15000]}}
      ]
    }}
    """

    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)

        dxf_file = generate_dxf_layout(data)

        with open(dxf_file, 'rb') as doc_file:
            await update.message.reply_document(document=doc_file, filename="architectural_plan.dxf", caption="تفضل، هذا ملف المخطط الهندسي بصيغة DXF جاهز.")
        
        if os.path.exists(dxf_file):
            os.remove(dxf_file)

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("حدث خطأ أثناء معالجة المخطط، تأكد من التفاصيل وأعد المحاولة.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
