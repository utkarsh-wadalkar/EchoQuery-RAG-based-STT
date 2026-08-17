
# EchoQuery Contracts


This directory contains the **source-of-truth contracts** shared across the EchoQuery application.


The purpose of these contracts is to allow the Frontend, Backend, AI/RAG Engine, and External Services to be developed independently without making assumptions about each other's internal implementation.


**Rule:** If an implementation disagrees with a contract, the implementation must be changed—not the contract—unless the team explicitly agrees to a contract version change.


---


## Contract Flow


```text
STT Provider
    │
    ▼
Transcript Schema
    │
    ▼
FastAPI Backend
    │
    ▼
Query Schema
    │
    ▼
Multilingual RAG Engine
    │
    ▼
Answer Schema
    │
    ▼
WebSocket Server Events
    │
    ▼
Frontend

The frontend also communicates with the backend through:

Frontend
    │
    ▼
WebSocket Client Events
    │
    ▼
FastAPI WebSocket
Files
transcript.schema.json

Defines the normalized transcript produced by the STT layer.

Both STT implementations must conform to this contract:

Sarvam Saaras v3
       │
       ├── production
       │
       ▼
Transcript


Voxtral Mini
       │
       └── testing
            │
            ▼
         Transcript

The rest of the application must not depend on provider-specific STT response formats.

query.schema.json

Defines the request passed from the backend into the RAG pipeline.

Transcript
    │
    ▼
Backend processing
    │
    ▼
Query
    │
    ▼
RAG Engine

The RAG engine receives the normalized query rather than a raw STT-provider response.

answer.schema.json

Defines the normalized result returned by the RAG engine.

The answer includes:

Generated answer
Response language
Grounding status
Retrieved sources
RAG latency information

The frontend should use this contract rather than depending on internal RAG implementation details.

websocket-client-events.schema.json

Defines JSON control events sent from the frontend to the backend.

Current client events:

session_start
audio_end
cancel

Audio data itself is not JSON encoded.

Audio is transmitted as binary WebSocket frames to avoid unnecessary base64 encoding and payload overhead.

websocket-server-events.schema.json

Defines events sent from the backend to the frontend.

Current server events:

transcript
processing
answer
error
complete

The frontend should rely only on these documented events and their schemas.

WebSocket Protocol
Client → Server

A typical request lifecycle is:

session_start
      │
      ▼
binary audio frame
      │
      ▼
binary audio frame
      │
      ▼
binary audio frame
      │
      ▼
audio_end

The client may cancel an active request:

session_start
      │
      ▼
binary audio frames
      │
      ▼
cancel
Server → Client

Successful request:

transcript
      │
      ▼
processing
      │
      ▼
transcript
      │
      ▼
processing
      │
      ▼
answer
      │
      ▼
complete

Failure:

...
 │
 ▼
error
 │
 ▼
complete(status = failed)

Cancellation:

cancel
 │
 ▼
complete(status = cancelled)
Supported Languages

EchoQuery supports the language set supported by the selected Sarvam-105B configuration:

en-IN  English
hi-IN  Hindi
bn-IN  Bengali
ta-IN  Tamil
te-IN  Telugu
kn-IN  Kannada
ml-IN  Malayalam
mr-IN  Marathi
gu-IN  Gujarati
pa-IN  Punjabi
od-IN  Odia

There is no translation layer in the EchoQuery architecture.

The intended flow is:

User Speech
    │
    ▼
STT
    │
    ▼
Detected Language
    │
    ▼
Multilingual RAG
    │
    ▼
Sarvam-105B
    │
    ▼
Answer in User Language

Languages outside the supported set should result in an UNSUPPORTED_LANGUAGE error rather than being silently translated.

Request Identification

Every request must have a unique:

request_id

The same request_id must be preserved across the complete request lifecycle:

STT
 ↓
Transcript
 ↓
Query
 ↓
RAG
 ↓
Answer
 ↓
WebSocket

This allows us to correlate logs, latency measurements, errors, and frontend events belonging to the same request.

Latency

RAG latency is measured separately from STT latency.

The target is:

RAG pipeline
────────────────────────
< 200 ms

The answer contract exposes individual measurements where available:

embedding_ms
retrieval_ms
reranking_ms
generation_ms
total_ms

STT latency is not included in total_ms.

This distinction is important for evaluating the system against the project's latency requirement.

Source Grounding

RAG answers must expose the retrieved sources used by the generation pipeline.

A source contains:

id
text
score
metadata

The text field is intentionally included so that the frontend can display the evidence supporting the generated answer.

This also allows the demo to visibly demonstrate:

Question
   ↓
Retrieved Evidence
   ↓
Generated Answer
Contract Rules
1. No provider leakage

The RAG engine must not depend on Sarvam-specific or Voxtral-specific response formats.

Both providers must produce the common Transcript contract.

2. No frontend dependency on internal RAG code

The frontend communicates through the API and WebSocket contracts only.

It must not depend on:

retriever.py
reranker.py
pipeline.py

or any other internal RAG implementation.

3. No binary data inside JSON events

Audio is transmitted through binary WebSocket frames.

4. No silent language fallback

Unsupported languages must return:

UNSUPPORTED_LANGUAGE

rather than being automatically translated.

5. Preserve request_id

All components must preserve the request identifier.

6. Validate at boundaries

Incoming and outgoing data should be validated against the corresponding contract at service boundaries.

Contract Ownership

| Contract                              | Primary Consumers      |
| ------------------------------------- | ---------------------- |
| `transcript.schema.json`              | STT, Backend, RAG      |
| `query.schema.json`                   | Backend, RAG           |
| `answer.schema.json`                  | RAG, Backend, Frontend |
| `websocket-client-events.schema.json` | Frontend, Backend      |
| `websocket-server-events.schema.json` | Backend, Frontend      |


The contracts are treated as versioned interfaces.

For the initial implementation:

Contract Version: v1

Do not modify an existing field, rename it, remove it, or change its meaning simply to make an implementation easier.

If a breaking change becomes necessary:

Discuss the change with the team.
Update all affected consumers.
Document the change.
Increment the contract version when appropriate.
Source of Truth
00-contracts/

is the authoritative definition of communication between the major EchoQuery components.

Implementation-specific models should be derived from these contracts:

JSON Schema
     │
     ├──► FastAPI / Pydantic models
     │
     ├──► Frontend / TypeScript types
     │
     └──► STT/RAG adapters

Do not independently redefine the same interface in multiple parts of the repository.