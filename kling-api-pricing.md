# Kling AI API Pricing

> Source: [Kling AI Developer Pricing](https://klingai.com/global/dev/pricing)
> Base URL (Singapore): `https://api-singapore.klingai.com`
> Last updated: March 2026

---

## Video Generation

### V3 Series (Latest - Per Second Billing)

| Model | Mode | Input | Cost/sec | Credits/sec |
|-------|------|-------|----------|-------------|
| kling-v3-omni | Standard | Text only | $0.084 | 0.6 |
| kling-v3-omni | Standard | With video | $0.112 | 0.8 |
| kling-v3-omni | Pro | Text only | $0.112 | 0.8 |
| kling-v3-omni | Pro | With video | $0.168 | 1.2 |
| kling-video-o1 | Standard | Text only | $0.084 | 0.6 |
| kling-video-o1 | Pro | With video | $0.168 | 1.2 |
| kling-v3 | Standard | Text only | $0.084 | 0.6 |
| kling-v3 | Pro | Text only | $0.126 | 0.9 |
| kling-v3 | Pro | With video | $0.168 | 1.2 |

**Estimated cost for common durations (V3 Standard text-only):**

| Duration | Standard | Pro |
|----------|----------|-----|
| 5 sec | $0.42 | $0.56 - $0.84 |
| 8 sec | $0.67 | $0.90 - $1.34 |
| 10 sec | $0.84 | $1.12 - $1.68 |

---

### V2 Series

| Model | Duration | Mode | Cost | Credits |
|-------|----------|------|------|---------|
| kling-v2-6 | 5s | Standard | $0.21 | 1.5 |
| kling-v2-6 | 5s | Pro | $0.70 | 5 |
| kling-v2-6 | 10s | Standard | $0.42 | 3 |
| kling-v2-6 | 10s | Pro | $1.68 | 12 |
| kling-v2-6 (motion ctrl) | per sec | — | $0.07 - $0.112 | — |
| kling-v2-5-turbo | 5s | Standard | $0.21 | 1.5 |
| kling-v2-5-turbo | 10s | Pro | $0.70 | 5 |
| kling-v2-1 | 5s | Standard | $0.28 | 2 |
| kling-v2-1 | 10s | Pro | $0.98 | 7 |
| kling-v2-1-master | 5s | — | $1.40 | 10 |
| kling-v2-1-master | 10s | — | $2.80 | 20 |
| kling-v2-master | 5s | — | $1.40 | 10 |
| kling-v2-master | 10s | — | $2.80 | 20 |

---

### V1 Series (Budget)

| Model | Duration | Mode | Cost | Credits |
|-------|----------|------|------|---------|
| kling-v1-6 | 5s | Standard | $0.28 | 2 |
| kling-v1-6 | 5s | Pro | $0.98 | 7 |
| kling-v1-5 | 5s | Standard | $0.28 | 2 |
| kling-v1-5 | 5s | Pro | $0.98 | 7 |
| kling-v1 | 5s | Standard | $0.14 | 1 |
| kling-v1 | 5s | Pro | $0.49 | 3.5 |

---

## Image Generation

| Model | Feature | Cost | Credits |
|-------|---------|------|---------|
| kling-image-o1 | Text-to-Image / Image-to-Image / Image Editing | $0.028 | 8 |
| kling-v2-1 | Text-to-Image | $0.014 | 4 |
| kling-v2 | Text-to-Image | $0.014 | 4 |
| kling-v2 | Multi-Image to Image | $0.056 | 16 |
| kling-v2 | Image Restyle | $0.028 | 8 |
| kling-v1-5 | Text/Image to Image (subject/face) | $0.028 | 8 |
| kling-v1 | Text/Image to Image | $0.0035 | 1 |

**Supported aspect ratios:** 1:1, 16:9, 4:3, 3:2, 2:3, 3:4, 9:16, 21:9

---

## Other APIs

| Feature | Cost | Credits | Unit |
|---------|------|---------|------|
| Lip-Sync | $0.07 | 0.1 | per 5 seconds |
| Text-to-Audio | $0.035 | 0.25 | per request |
| Video-to-Audio | $0.035 | 0.25 | per request |
| Avatar | $0.056 - $0.112 | 0.4 - 0.8 | per second |
| Face Recognition | $0.007 | — | per access |
| Speech Synthesis | $0.007 | — | per access |
| Voice Control | $0.007 | — | per access |
| Virtual Try-On (v1/v1.5) | $0.07 | 1 | per request |
| Image Editing (Expansion) | $0.028 | 8 | per request |

---

## Billing Rules

- **Failed generations** are NOT charged
- Concurrent request limits apply per package tier
- Unused balances **expire** (no rollover)
- Volume-tiered discounts available for bulk purchases
- Enterprise/custom packages available via consultation

---

## Quick Reference: Cost for 10s Video (Closest to 8s)

| Model | Mode | Cost |
|-------|------|------|
| kling-v1 (cheapest) | Standard 5s | $0.14 |
| kling-v2-5-turbo (best value) | Standard 5s | $0.21 |
| kling-v2-6 | Standard 10s | $0.42 |
| kling-v2-6 | Pro 10s | $1.68 |
| kling-v3 (latest) | Standard 10s | $0.84 |
| kling-v3 (latest) | Pro 10s | $1.26 - $1.68 |
