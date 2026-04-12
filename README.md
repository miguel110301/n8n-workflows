# n8n Workflows

Production-grade n8n workflow collection built for real business operations. Each workflow is documented, fault-tolerant, and ready to import.

## Workflows

### 1. WhatsApp OCR Pipeline
**File:** `whatsapp-ocr/workflow.json`

Processes delivery receipt photos sent via WhatsApp. Extracts structured data using GPT-4o Vision, validates against business rules, persists to PostgreSQL, and replies automatically in under 30 seconds.

**Key patterns:**
- Native WhatsApp Business API node
- GPT-4o Vision for OCR and data extraction
- Human-in-the-Loop escalation on ambiguous documents
- Error Trigger branch with dev team notification
- Full execution logging

**Results:** Eliminated 9+ hours/day of manual coordination. 500+ daily validations with zero human intervention.

### 2. Gamma Agent — Async AI Presentation Generator
**File:** `gamma-agent/workflow.json`

Fully asynchronous AI agent that ingests raw data via Telegram, generates presentations via Gamma API, pauses for human approval, and schedules email delivery at optimal time — zero manual steps.

**Key patterns:**
- Human-in-the-Loop using `$getWorkflowStaticData('global')` for cross-execution state persistence
- Wait node with resume-at-datetime for deferred execution
- Telegram bot for approval/rejection interface
- Approve/Reject routing via Switch node

## How to Import

1. Open your n8n instance
2. Go to **Workflows → Import**
3. Select the `.json` file
4. Configure your credentials in each node
5. Activate the workflow

## Environment Variables Required

```env
WHATSAPP_TOKEN=your_token
WHATSAPP_PHONE_ID=your_phone_id
OPENAI_API_KEY=your_key
DJANGO_API_URL=your_api_url
TELEGRAM_BOT_TOKEN=your_token
GAMMA_API_KEY=your_key
```

## Related

- [Portfolio](https://migueldev.com.mx)
- [WhatsApp OCR Pipeline — full implementation](https://github.com/miguel110301/whatsapp-ocr-pipeline)