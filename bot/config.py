from dotenv import load_dotenv
import os

load_dotenv()

telegram_config = {
    'token': os.environ['TELEGRAM_BOT_TOKEN'],
    'admin_user_ids': os.environ.get('ADMIN_USER_IDS', '-'),
    'allowed_user_ids': os.environ.get('ALLOWED_TELEGRAM_USER_IDS', '*'),
    'enable_quoting': os.environ.get('ENABLE_QUOTING', 'true').lower() == 'true',
    'enable_image_generation': os.environ.get('ENABLE_IMAGE_GENERATION', 'true').lower() == 'true',
    'enable_transcription': os.environ.get('ENABLE_TRANSCRIPTION', 'true').lower() == 'true',
    'monthly_user_budgets': os.environ.get('MONTHLY_USER_BUDGETS', '*'),
    'monthly_guest_budget': float(os.environ.get('MONTHLY_GUEST_BUDGET', '100.0')),
    'stream': os.environ.get('STREAM', 'true').lower() == 'true',
    'proxy': os.environ.get('PROXY', None),
    'voice_reply_transcript': os.environ.get('VOICE_REPLY_WITH_TRANSCRIPT_ONLY', 'true').lower() == 'true',
    'ignore_group_transcriptions': os.environ.get('IGNORE_GROUP_TRANSCRIPTIONS', 'true').lower() == 'true',
    'group_trigger_keyword': os.environ.get('GROUP_TRIGGER_KEYWORD', ''),
    'token_price': float(os.environ.get('TOKEN_PRICE', 0.002)),
    'image_prices': [float(i) for i in os.environ.get('IMAGE_PRICES',"0.016,0.018,0.02").split(",")],
    'transcription_price': float(os.environ.get('TOKEN_PRICE', 0.006)),
}

discord_config = {
    'token': os.environ.get('DISCORD_TOKEN', ''),
}

sdwebuiapi_config = {
    'host': os.environ['HOST'],
    'port': int(os.environ.get('PORT', '80')),
    'allowed_user_ids': os.environ.get('ALLOWED_TELEGRAM_USER_IDS', '*'),
    'use_https': os.environ.get('USE_HTTPS', 'false').lower() == 'true',
}