import requests
import json
import logging
import config

# إعداد السجلات لمراقبة الأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = config.OPENROUTER_API_KEY
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/railway/app", # مطلوب أحياناً من OpenRouter
        }
        self.model = "google/gemini-2.0-flash-001" # الموديل الافتراضي

    def _send_request(self, messages, json_mode=False):
        """دالة داخلية للتعامل مع طلبات API"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                self.url, 
                headers=self.headers, 
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return content
            else:
                logger.error(f"OpenRouter Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"AI Connection Exception: {str(e)}")
            return None

    def generate_post(self, prompt, context="English Teacher"):
        """توليد منشور احترافي للنشر في القنوات"""
        system_instruction = (
            f"You are an expert {context}. Create an engaging Telegram post. "
            "Use emojis, clear formatting, and professional tone. "
            "The output should be ready to publish directly."
        )
        
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]
        return self._send_request(messages)

    def generate_quiz(self, topic):
        """توليد اختبار (Quiz) بصيغة JSON متوافقة مع تليجرام"""
        system_instruction = (
            "You are a specialized JSON generator for English quizzes. "
            "Your response must be ONLY a valid JSON object. "
            "No markdown, no talk, just JSON."
        )
        
        prompt = (
            f"Create a multiple choice English quiz about: {topic}. "
            "Format: {\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"correct_index\": 0}"
        )
        
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]
        
        raw_response = self._send_request(messages)
        
        if raw_response:
            try:
                # تنظيف الرد من أي علامات Markdown قد يضيفها الموديل بالخطأ
                clean_content = raw_response.strip()
                if clean_content.startswith("```"):
                    clean_content = clean_content.split("```")[1]
                    if clean_content.startswith("json"):
                        clean_content = clean_content[4:]
                
                return json.loads(clean_content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON Parsing Error: {e} | Raw: {raw_response}")
                return None
        return None

    def summarize_text(self, text):
        """تلخيص المحتوى الطويل"""
        prompt = f"Summarize the following text into short bullet points for Telegram: \n\n{text}"
        messages = [{"role": "user", "content": prompt}]
        return self._send_request(messages)

    def rephrase(self, text):
        """إعادة صياغة النص لجعله أكثر احترافية"""
        prompt = f"Improve and rephrase this text for a professional Telegram audience: \n\n{text}"
        messages = [{"role": "user", "content": prompt}]
        return self._send_request(messages)

# تصدير نسخة جاهزة للاستخدام
ai_handler = AIService()
      
