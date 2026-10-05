# agent.py
import asyncio
from datetime import datetime, timedelta
import uuid
# band_sdk imports are isolated here to keep the core code pure
from band_sdk import BandAgentMesh, band_tool
from darkfactory import RegionalBookingEngine, Table, Reservation, NegotiationAgents

# 1. Initialize the Multi-Agent Coordination Mesh Layer
mesh = BandAgentMesh(agent_id="tablekeeper_mesh_coordinator")

# 2. Mock instance states for the desktop runtime evaluation
# This provides persistent memory containers for the agents to mutate
nyc_engine = RegionalBookingEngine("NYC_1", "America/New_York", [Table("T1", 2, "NYC_1"), Table("T2", 4, "NYC_1")])
lon_engine = RegionalBookingEngine("LON_1", "Europe/London", [Table("L1", 2, "LON_1"), Table("L2", 4, "LON_1")])

@band_tool(name="allocate_reservation_slot")
async def allocate_reservation_slot(location_id: str, party_size: int, time_iso: str) -> str:
    """
    Exposes Track 1 allocation directly to the BAND Desktop context wrapper.
    Ensures that concurrency limits are managed under zero double-booking conditions.
    """
    try:
        # Convert incoming string configurations to explicit native Python formats
        target_time = datetime.fromisoformat(time_iso)
        engine = nyc_engine if location_id == "NYC_1" else lon_engine
        
        new_res = Reservation(
            res_id=str(uuid.uuid4()),
            party_size=int(party_size),
            start_time=target_time,
            end_time=target_time + timedelta(hours=1)
        )
        
        # Step A: Attempt standard localized queue booking
        success, msg = await engine.attempt_booking(new_res)
        if success:
            return f"SUCCESS: Table {new_res.table_id} confirmed for location {location_id}."
        
        # Step B: If blocked, trigger the Builder-Verifier negotiation flow
        partners_pool = [lon_engine if location_id == "NYC_1" else nyc_engine]
        proposals = await NegotiationAgents.builder_propose_alternatives(engine, new_res, partners=partners_pool)
        decision = await NegotiationAgents.verifier_audit(proposals, new_res)
        
        if decision:
            alt_eng, alt_start, _ = decision
            new_res.start_time = alt_start
            new_res.end_time = alt_start + timedelta(hours=1)
            _, final_msg = await alt_eng.attempt_booking(new_res)
            return f"NEGOTIATED: Shifted to {alt_eng.location_id} at {alt_start.isoformat()}. Status: {final_msg}"
            
        return "REJECTED: Mapped alternatives occupied."
    except Exception as e:
        return f"ERROR: Processing failed -> {str(e)}"
