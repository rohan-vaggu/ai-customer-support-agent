# API Response Flow Explanation

## Question: "As a student should i buy an iphone or macbook"

### Response Flow Chart:

```
User asks: "As a student should i buy an iphone or macbook"
    ↓
Check if question is cached?
    ↓ (NO - First time)
Call Gemini API
    ↓
API Response Success ✅
    ↓
RETURN: API Response
(The bot's actual response message)
```

---

## Answer to Your 3 Questions:

### 1️⃣ **What Will Be Returned?**

The Gemini API will return:
```
"I'm unable to provide personalized recommendations for which product 
might be better suited for your student needs, as my function is to 
provide information from the NovaCart knowledge base.

However, I can share details about both the iPhone 15 and MacBook Air 
M3 to help you decide! The iPhone 15 is available for ₹74,999 (with 
an instant discount) and the MacBook Air M3 is ₹1,04,999 (with a 
₹10,000 instant discount). Both come with a 1-year manufacturer warranty.

If you have specific questions about features, pricing, or offers for 
either product, please feel free to ask!"
```

### 2️⃣ **Is It Mock Response or API Request?**

**FIRST TIME REQUEST**: ✅ **API Request to Gemini**
- Reason: Question is not in cache yet
- Server logs show: `DEBUG - Response object: response: GenerateContentResponse(...)`

**SECOND TIME REQUEST**: ✅ **CACHED (No API Call)**
- Reason: Same question was already asked
- Server logs show: `DEBUG - Using cached response for: As a student should i buy an iphone or macbook`
- Result: Instant response, saves API quota

### 3️⃣ **If API Limit Reached (Quota Exceeded)?**

When Google Gemini API quota is exceeded:

```
User asks: "As a student should i buy an iphone or macbook"
    ↓
Check cache
    ↓ (NO - First time)
Try to call Gemini API
    ↓ ❌
ResourceExhausted Exception
    ↓
Trigger get_mock_response()
    ↓
Check keywords: "iphone" ✅ AND "macbook" ✅ found
    ↓
RETURN: Mock Product Response
```

**Mock Response Returned:**
```
"We have three main products: iPhone 15 (₹74,999 with discount), 
Samsung Galaxy S24 (₹71,999 with discount), and MacBook Air M3 
(₹1,04,999 with discount). All come with instant discounts and 
1-year warranty. Which one interests you?"
```

---

## Default Message Behavior

### ❌ If All Fails:
If the question doesn't match ANY mock response keywords:

```
"I'd be happy to help! Could you ask more specifically about products, 
prices, shipping, returns, or payments? You can also contact our team 
at +91-9876543210 or support@novacart.com."
```

### ✅ Mock Response Triggers On:
- **Product questions**: Contains "iphone", "samsung", "macbook", "product", "what do you have", "catalog"
- **Pricing**: Contains "discount", "price", "cost", "offer", "how much"
- **Shipping**: Contains "shipping", "delivery", "how long", "when will", "arrive", "track"
- **Returns**: Contains "return", "refund", "damaged", "warranty", "exchange"
- **Payment**: Contains "payment", "pay", "card", "upi", "transfer", "method"
- **EMI**: Contains "emi", "installment", "payment plan"
- **Greeting**: Contains "hi", "hello", "hey", "good morning", "good evening"

---

## Real Test Results:

### Test 1: First Request
```
🔵 Request: "As a student should i buy an iphone or macbook"
🟢 Source: Gemini API (not cached)
⏱️ Time: ~1-2 seconds
📊 Tokens Used: 1057 prompt + 142 response = 1199 tokens
```

### Test 2: Second Identical Request
```
🔵 Request: "As a student should i buy an iphone or macbook"
🟢 Source: Cache (NO API CALL)
⏱️ Time: <100ms (instant)
📊 Tokens Used: 0 (saved quota!)
```

---

## Summary Table

| Aspect | API Available | API Quota Exceeded |
|--------|---------------|-------------------|
| **Response Source** | Gemini API | Mock Response Function |
| **Quality** | Full contextual AI response | Keyword-matched template |
| **Speed** | 1-2 seconds | <100ms (instant) |
| **Caching** | Cached after 1st call | Still cached, no API hit |
| **Tokens Used** | ~1000-1500 per question | 0 tokens |
| **Example Response** | Thoughtful, context-aware | Simple, informative template |

