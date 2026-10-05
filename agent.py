# agents.py
import asyncio
from darkfactory import RegionalBookingEngine, Reservation, Table
# Note: BAND Desktop automatically injects mesh capabilities inside its runner environment
from band import BandAgentMesh 

mesh = BandAgentMesh(agent_id="booking_mesh_coordinator")

class BandNegotiationAgents:
    @mesh.register_agent(name="SlotBuilderAgent")
    class BuilderAgent:
        def __init__(self, engine: RegionalBookingEngine, partners: List[RegionalBookingEngine]):
            self.engine = engine
            self.partners = partners

        @band_tool(description="Synthesizes system proposals for shifting schedules or cross-node venues.")
        async def propose_alternatives(self, res_id: str, party_size: int, start_iso: str, end_iso: str) -> dict:
            start = datetime.fromisoformat(start_iso)
            end = datetime.fromisoformat(end_iso)
            proposals = []
            
            # 1. Scan localized temporal slots
            for shift_hours in [1, 2]:
                new_start = start + timedelta(hours=shift_hours)
                new_end = end + timedelta(hours=shift_hours)
                table_id = await self.engine.check_availability(new_start, new_end, party_size)
                if table_id:
                    proposals.append({
                        "node": self.engine.location_id, 
                        "start": new_start.isoformat(), 
                        "end": new_end.isoformat()
                    })

            # 2. Query partner environments connected to the shared control plane mesh
            for partner in self.partners:
                p_start = start.astimezone(partner.tz)
                p_end = end.astimezone(partner.tz)
                table_id = await partner.check_availability(p_start, p_end, party_size)
                if table_id:
                    proposals.append({
                        "node": partner.location_id, 
                        "start": p_start.isoformat(), 
                        "end": p_end.isoformat()
                    })

            # Hand off context asynchronously to the Verifier agent inside the Band Room using an @mention routing trigger
            await mention_agent(
                agent_name="SlotVerifierAgent",
                message=f"Reviewing {len(proposals)} options compiled for reservation {res_id}.",
                payload={"proposals": proposals, "res_id": res_id, "party_size": party_size}
            )
            return {"status": "Dispatched to Verifier", "proposals_count": len(proposals)}

    @mesh.register_agent(name="SlotVerifierAgent")
    class VerifierAgent:
        def __init__(self, engines: Dict[str, RegionalBookingEngine]):
            self.engines = engines

        @band_tool(description="Enforces strict double-booking bounds checking and issues final authority approval.")
        async def verifier_audit(self, proposals: list, party_size: int) -> Optional[dict]:
            for prop in proposals:
                target_engine = self.engines.get(prop["node"])
                if not target_engine:
                    continue
                
                start = datetime.fromisoformat(prop["start"])
                end = datetime.fromisoformat(prop["end"])
                
                # Direct check against the isolated engine ledger status
                table_id = await target_engine.check_availability(start, end, party_size)
                if table_id:
                    return {
                        "approved": True,
                        "node": prop["node"],
                        "start": prop["start"],
                        "end": prop["end"],
                        "table_id": table_id
                    }
            return {"approved": False, "reason": "All structural alternative matrices occupied."}

