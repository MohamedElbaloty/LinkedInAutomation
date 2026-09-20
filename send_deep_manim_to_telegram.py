import asyncio
import os
import sys
from pathlib import Path
from PIL import Image

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from telegram import Bot
from telegram.constants import ParseMode
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from fetcher import mark_as_posted

async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    chat_id = TELEGRAM_CHAT_ID
    print(f"Delivering Deep Manim AI news bundle to Telegram chat: {chat_id}...")

    # 1. Crop the pristine Deep Manim tile from the Flow generation state
    final_state_img = Path("output_images/flow_final_state.png")
    cropped_manim_path = Path("output_images/deep_manim_flow_result.png")
    
    if final_state_img.exists():
        with Image.open(final_state_img) as im:
            # The top-left tile in 1280x720 canvas
            # Bounding box approximately: left=245, top=105, right=740, bottom=388
            crop_box = (248, 105, 738, 388)
            tile_crop = im.crop(crop_box)
            tile_crop.save(cropped_manim_path)
            print("Pristine Deep Manim tile cropped and saved!")
    
    # 2. Prepare the Comprehensive Technical Post
    short_hook = (
        "🚀 ثورة معمارية جديدة في عالم الـ AI: مبتكر تقنية الـ RLHF في OpenAI يطلق نموذج Jev للتخلص تماماً من الهلوسة وتسريع الأتمتة البرمجية!"
    )

    post_text = """🚀 **ثورة معمارية جديدة: مبتكر RLHF في OpenAI يطلق نموذج Jev لإنهاء عصر هلوسة النماذج وتسريع الأتمتة!**

في تحول معماري قد يغير قواعد بناء البرمجيات الذكية، أعلن Diogo Almeida (أحد أبرز باحثي OpenAI المشاركين في بناء ChatGPT والمبتكر المشارك لتقنية الـ RLHF) عن إطلاق نموذج جديد يُدعى **Jev** عبر شركته الناشئة **TypeSafe AI**.

💡 **جذر المشكلة الهندسية:**
يقول Almeida: *"امتلكنا صاعقة في زجاجة (Lightning in a bottle) لكنها غير عملية للأتمتة؛ لأننا دربنا النماذج على إتقان لغة البشر، بينما أجهزة الكمبيوتر والأنظمة البرمجية تتحدث بلغة مختلفة تماماً مبنية على المحددات المنطقية والاحتمالات الصارمة."*

---

🔬 **التحليل المعماري والهندسي (Architectural Breakdown):**

1️⃣ **الانتقال من التوليد اللغوي (Autoregressive Token Generation) إلى القرارات المعايرة (Calibrated Decisions):**
بدلاً من حلقة التوليد التسلسلية البطيئة المكلفة $O(N)$ لتوقع الكلمة التالية عبر قاموس ضخم، يعمل Jev بنموذج Transformer متطور لا يخرج نصوصاً، بل يسقط المخرجات مباشرة في خطوة واحدة (Single Forward Pass) إلى متجهات احتمالية معايرة بدقة فوق Schema محددة مسبقاً.

2️⃣ **Zero Hallucination by Mathematical Constraint:**
الهلوسة في الـ LLMs التقليدية ليست خطأ عشوائياً، بل خاصية حتمية لطبيعة التوزيع اللغوي. في Jev، المطور هو من يعرّف فضاء المخرجات (Decision Simplex) مسبقاً؛ وبالتالي يصبح احتمال خروج النموذج عن النطاق الرياضي صفراً رياضياً!

3️⃣ **انهيار تكلفة الاستدلال (Inference Economics):**
- مخرجات النموذج مجانية بالكامل (Zero Output Cost).
- احتساب التوكنات للمدخلات يُقاس بالمليارات بدلاً من الملايين.
- انعدام الحاجة لتخزين وتضخيم ذاكرة الـ KV Cache المصاحبة للنصوص الطويلة.

---

📐 **مخطط التحريك الرياضي (Deep Manim Blueprint - 3Blue1Brown Style):**

🎬 **تصور المشهد الرياضي الهندسي في Manim:**
- **Scene 1 (The Bottleneck):** محاكاة شجرة التوليد التسلسلي للـ LLM التقليدي $P(w_t | w_{<t})$ كمسار عشوائي متشعب يتلاشى فيه التركيز وتتراكم فيه احتمالات الخطأ (Drift).
- **Scene 2 (The Linear Projection):** تحول مساحة التضمين (Latent Embedding Space $\mathbf{h} \in \mathbb{R}^d$) عبر مصفوفة أوزان مضغوطة $W_O$ مباشرة إلى مجسم احتمالي ثلاثي الأبعاد (Probability Simplex $\Delta^K$).
- **Scene 3 (Calibrated Boundary):** مسار متجهات مضيئة باللون الأزرق النيلي (Cyan Tensors) تنحدر بسلاسة نحو نقطة القرار الرياضي الدقيق (Typed Decision Vector) في زمن زمني موحد $O(1)$.

---

🎬 **Google Flow Prompt المستخدم في التوليد الحي:**
`"A 3Blue1Brown Deep Manim mathematical animation on dark slate background (#0B0F19). Visualizing Jev transformer model: calibrated probability vectors over decision simplex, zero hallucinations, glowing vector tensors, clean LaTeX notation, 16:9 widescreen"`

---

💬 **سؤال للنقاش الهندسي (CTA):**
هل تعتقد أن مستقبل الـ Agentic AI للأتمتة والـ Enterprise Systems سيكون للنماذج ذات المخرجات المعايرة المحددة (Typed Models) بدلاً من نماذج المحادثة الضخمة متسعة الاحتمالات؟

#AI #SoftwareEngineering #AgenticAI #MachineLearning #DeepManim #Transformers #OpenAI #GoogleFlow"""

    # 3. Deliver to Telegram
    # A) Send the Cropped Deep Manim Result generated on Google Flow
    target_photo = cropped_manim_path if cropped_manim_path.exists() else final_state_img
    with open(target_photo, "rb") as photo_file:
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo_file,
            caption="🎬 **[Deep Manim - Google Flow Technical Output]**\n" + short_hook,
            parse_mode=ParseMode.MARKDOWN,
        )
    print("Sent Deep Manim visual to Telegram!")

    # B) Send the Full Technical LinkedIn Post
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=post_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        print(f"Markdown send failed ({e}), sending plain text...")
        await bot.send_message(
            chat_id=chat_id,
            text=post_text,
            parse_mode=None,
        )
    print("Sent full post text to Telegram!")

    # C) Send Google Flow Live Execution Proof Screenshot
    live_proof = Path("output_images/flow_live_execution.png")
    final_proof = Path("output_images/flow_final_state.png")
    
    if final_proof.exists():
        with open(final_proof, "rb") as proof_file:
            await bot.send_photo(
                chat_id=chat_id,
                photo=proof_file,
                caption="📸 **[Google Flow Live Proof]**\nإثبات العمل المباشر: تم إرسال الـ Prompt إلى مشروعك في Google Flow وتم توليد الفيديو الرياضي التقني بنجاح داخل مساحة العمل!",
                parse_mode=ParseMode.MARKDOWN,
            )
        print("Sent Flow live proof to Telegram!")

    # D) Send uncompressed high quality document
    with open(target_photo, "rb") as doc_file:
        await bot.send_document(
            chat_id=chat_id,
            document=doc_file,
            caption="📁 [Master Quality Asset - Deep Manim Tensor Visual]",
        )

    # 4. Mark article as posted in SQLite database
    article_id = "jev-typesafe-ai-model-2026-09-18"
    article_title = "A new kind of AI model from a ChatGPT inventor is thrilling developers"
    mark_as_posted(article_id, article_title, "2026-09-18")
    print("Marked article as posted in SQLite database!")
    print("ALL DONE SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
