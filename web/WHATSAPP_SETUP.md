# WhatsApp Integration Setup

To enable WhatsApp digest sending, you'll need to configure Twilio:

## Steps:

1. **Create Twilio Account**
   - Go to https://www.twilio.com/whatsapp/request-access
   - Request WhatsApp API access (free tier available)
   - Get your Account SID and Auth Token

2. **Get WhatsApp Sandbox Number**
   - In Twilio Console, navigate to WhatsApp
   - Get your sandbox number (format: +1XXXXX)

3. **Add Environment Variables**
   
   Create `.env.local` in `/web` directory:
   ```
   TWILIO_ACCOUNT_SID=your_account_sid_here
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_WHATSAPP_NUMBER=+1234567890
   ```

4. **For Vercel Production**
   - Go to Vercel Dashboard → Project Settings → Environment Variables
   - Add the three env vars above
   - Redeploy

## Demo Mode

Without Twilio credentials, the app runs in **demo mode**:
- Shows message preview
- Generates digest formatting
- Returns success confirmation
- Prompts to configure Twilio for real sending

## Costs

- Twilio free tier: $25 free credit
- Cost per WhatsApp message: ~$0.02-$0.05 AUD
- Inbound messages: included in free tier

## Alternative Services

- **Vonage** (similar pricing)
- **Gupshup** (free tier for development)
- **MessageBird** (free trial)
