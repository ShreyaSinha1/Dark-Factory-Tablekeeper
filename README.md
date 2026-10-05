# Dark Factory Tablekeeper (Track 1)

An autonomous, multi-agent restaurant reservation engine built for the **WeAreDevelopers x BAND Dark Factory Hackathon**. This system features strict time-slot allocation isolation, multi-timezone coordinate matching, automated escrow holds, and an independent cross-node distributed state auditor.

## 🏗️ Architecture Design & Guardrails

The service isolates core business constraints from the platform multi-agent routing mesh layer (`band_sdk`) to prevent runtime dependency cr
ashes:

1. **Time-Slot Allocation Isolation (`asyncio.Lock`):** Protects isolated regional databases (`RegionalBookingEngine`) from concurrent race condition conflicts during booking spikes.
2. **Smart-Capacity Waitlist Manager:** A negotiation workflow that detects temporal collisions and dynamically calculates internal time shifts or alternative partner location availability.
3. **Automated Escrow Hold (`EscrowHoldCoordinator`):** Asynchronously tracks cancellation parameters and confirmation timelines to execute automatic penalty collection or deposit releases.
4. **Independent Centralized Auditor (`CentralizedAuditor`):** A detached evaluation system that runs concurrent cross-ledger sanity audits to ensure absolute data validity.

## 🚀 Workspace File Tree

```text
DARK-FACTORY-TABLEKEEPER/
├── darkfactory.py          # Core Simulation & Business Logic Engine
├── agent.py                # BAND Desktop Tool Mappings & Wrappers
├── agent_entry.py          # Platform Daemon Entry Lifecycle Hook
├── band.json               # Generic Hackathon Mandate Configurations
└── README.md               # Technical Documentation Manifest
```

## 💻 Local Testing & Verification Sweep

To run the concurrent validation scenario locally on your machine outside the sandbox environment, execute:

```powershell
py darkfactory.py
```

### Verified Terminal Log Trace Output:
```text
!!! INITIATING CORE SIMULATION LEDGER !!!
[Escrow] Locked $50.0 deposit security window for Res bb55b37a-9d6c-455f-9f60-a177a3cdb7be.
Res 1 Status: True -> Successfully held table T2.

[Waitlist System Processing Overlap Collision Request...]
Res 2 Direct Booking Attempt: False -> No spatial/temporal matrix gap matching criteria found.
[Agent Success] Reallocated Res 2 to Venue Node: NYC_1 at 04:00 PM. Status: Successfully held table T2.

[Auditor Log] Starting Cross-Node Distributed State Audit...
[Auditor Log] Complete State Validated. Zero Double-Bookings Detected Across Ledgers.
```

## 🛠️ Deploying onto BAND Desktop App

1. Launch the **BAND Desktop Application**.
2. Mount this repository workspace directory (`DARK-FACTORY-TABLEKEEPER`).
3. Select your `band.json` profile to boot up your generic multi-agent capabilities.
