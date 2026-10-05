import asyncio
from datetime import datetime, timedelta
import zoneinfo
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import uuid

# ==========================================
# CORE TYPES & DATASTRUCTURES
# ==========================================
@dataclass(frozen=True)
class Table:
    table_id: str
    capacity: int
    regional_id: str  # Maps directly to visual explorer requirements

@dataclass
class Reservation:
    res_id: str
    party_size: int
    start_time: datetime  # Timezone-aware
    end_time: datetime    # Timezone-aware
    table_id: Optional[str] = None
    status: str = "INIT"  # INIT, PENDING, CONFIRMED, CANCELLED, NOSHOW
    escrow_held: float = 0.0

# ==========================================
# MULTI-LOCATION MULTI-TIMEZONE ENGINE
# ==========================================
class RegionalBookingEngine:
    """Manages isolated region ledgers and state mutation under explicit local locks."""
    def __init__(self, location_id: str, timezone_str: str, tables: List[Table]):
        self.location_id = location_id
        self.tz = zoneinfo.ZoneInfo(timezone_str)
        self.tables = sorted(tables, key=lambda t: t.capacity)
        self.reservations: Dict[str, Reservation] = {}
        self.lock = asyncio.Lock()

    def get_local_time(self, dt: datetime) -> datetime:
        return dt.astimezone(self.tz)

    async def check_availability(self, start: datetime, end: datetime, party_size: int) -> Optional[str]:
        """Scans for an open un-booked table fitting matching sizing blocks."""
        eligible_tables = [t for t in self.tables if t.capacity >= party_size]
        if not eligible_tables:
            return None

        # Filter out inactive states (Only evaluate active PENDING or CONFIRMED holds)
        active_res = [r for r in self.reservations.values() if r.status in ("INIT", "PENDING", "CONFIRMED")]
        
        for table in eligible_tables:
            overlap = False
            for res in [r for r in active_res if r.table_id == table.table_id]:
                # STRICT OVERLAP CHECK: True if intervals intersect at all
                if not (end <= res.start_time or start >= res.end_time):
                    overlap = True
                    break
            if not overlap:
                return table.table_id
        return None

    async def attempt_booking(self, res: Reservation) -> Tuple[bool, str]:
        """Enforces Time-Slot Allocation Isolation to eliminate double-booking."""
        async with self.lock:
            loc_start = res.start_time.astimezone(self.tz)
            if loc_start.hour < 11 or loc_start.hour > 22:
                return False, f"Target slot ({loc_start.hour}:00) falls outside operational regional hours (11:00-23:00)."

            assigned_table = await self.check_availability(res.start_time, res.end_time, res.party_size)
            if assigned_table:
                res.table_id = assigned_table
                res.status = "PENDING"
                self.reservations[res.res_id] = res
                return True, f"Successfully held table {assigned_table}."
            return False, "No spatial/temporal matrix gap matching criteria found."

# ==========================================
# SMART-CAPACITY WAITLIST MANAGER (LOCAL MATH)
# ==========================================
class NegotiationAgents:
    """Implements core algorithmic shift capabilities used by the outer agent layer."""
    @staticmethod
    async def builder_propose_alternatives(
        engine: RegionalBookingEngine, res: Reservation, partners: List[RegionalBookingEngine]
    ) -> List[Tuple[RegionalBookingEngine, datetime, datetime]]:
        proposals = []
        
        # 1. Look for internal time shifts (+60 mins or +120 mins)
        time_shifts = [timedelta(hours=1), timedelta(hours=2)]
        for shift in time_shifts:
            new_start = res.start_time + shift
            new_end = res.end_time + shift
            table_id = await engine.check_availability(new_start, new_end, res.party_size)
            if table_id:
                proposals.append((engine, new_start, new_end))
                
        # 2. Look for fallback options at cooperative partner venues
        for partner in partners:
            p_start = res.start_time.astimezone(partner.tz)
            p_end = res.end_time.astimezone(partner.tz)
            table_id = await partner.check_availability(p_start, p_end, res.party_size)
            if table_id:
                proposals.append((partner, p_start, p_end))
                
        return proposals

    @staticmethod
    async def verifier_audit(
        proposals: List[Tuple[RegionalBookingEngine, datetime, datetime]], res: Reservation
    ) -> Optional[Tuple[RegionalBookingEngine, datetime, datetime]]:
        for target_engine, start, end in proposals:
            table_id = await target_engine.check_availability(start, end, res.party_size)
            if table_id:
                return target_engine, start, end
        return None

# ==========================================
# NO-SHOW PENALTY & HOLD SYSTEM
# ==========================================
class EscrowHoldCoordinator:
    def __init__(self, grace_period_minutes: int = 15, deposit_amount: float = 50.0):
        self.grace_period = timedelta(minutes=grace_period_minutes)
        self.deposit_amount = deposit_amount

    async def secure_hold(self, res: Reservation):
        res.escrow_held = self.deposit_amount
        print(f"[Escrow] Locked ${self.deposit_amount} deposit security window for Res {res.res_id}.")

    async def execute_clock_monitor(self, engine: RegionalBookingEngine, res: Reservation):
        cutoff_time = res.start_time + self.grace_period
        now = datetime.now(res.start_time.tzinfo)
        
        delay_seconds = (cutoff_time - now).total_seconds()
        # Ensure negative or near-zero values yield instantly without locking up the loop
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        else:
            await asyncio.sleep(0.01) # Small yields prevent thread choking
            
        async with engine.lock:
            current_res = engine.reservations.get(res.res_id)
            if current_res and current_res.status == "PENDING":
                current_res.status = "NOSHOW"
                print(f"[Escrow Trigger] Penalty charged! Host captured ${current_res.escrow_held} from Res {res.res_id} due to no-show.")

# ==========================================
# GLOBAL SYNC AUDITOR
# ==========================================
class CentralizedAuditor:
    @staticmethod
    async def global_sanity_check(engines: List[RegionalBookingEngine]):
        print("\n[Auditor Log] Starting Cross-Node Distributed State Audit...")
        all_ok = True
        for engine in engines:
            async with engine.lock:
                allocated_spans: Dict[str, List[Tuple[datetime, datetime]]] = {}
                for res in engine.reservations.values():
                    if res.status not in ("INIT", "PENDING", "CONFIRMED"):
                        continue
                    if res.table_id not in allocated_spans:
                        allocated_spans[res.table_id] = []
                    
                    for start, end in allocated_spans[res.table_id]:
                        if not (res.end_time <= start or res.start_time >= end):
                            print(f"[CRITICAL DETECTED] Overlap error at node {engine.location_id} on Table {res.table_id}!")
                            all_ok = False
                    allocated_spans[res.table_id].append((res.start_time, res.end_time))
        if all_ok:
            print("[Auditor Log] Complete State Validated. Zero Double-Bookings Detected Across Ledgers.\n")

# ==========================================
# RUNTIME ENVIRONMENT SWEEP
# ==========================================
async def main():
    nyc_tables = [Table("T1", 2, "NYC_1"), Table("T2", 4, "NYC_1")]
    lon_tables = [Table("L1", 2, "LON_1"), Table("L2", 4, "LON_1")]
    
    nyc_engine = RegionalBookingEngine("NYC_1", "America/New_York", nyc_tables)
    lon_engine = RegionalBookingEngine("LON_1", "Europe/London", lon_tables)
    
   # escrow_system = EscrowHoldCoordinator(grace_period_minutes=0, deposit_amount=50.0)
        # Set to -1 so the clock monitor expires instantly during your test sweep!
    escrow_system = EscrowHoldCoordinator(grace_period_minutes=-1, deposit_amount=50.0)

    
    target_tz = zoneinfo.ZoneInfo("America/New_York")
    now_dt = datetime.now(target_tz)
    base_time = datetime(year=now_dt.year, month=now_dt.month, day=now_dt.day, hour=15, minute=0, tzinfo=target_tz)
    
    res1 = Reservation(str(uuid.uuid4()), 4, base_time, base_time + timedelta(hours=1))
    success, msg = await nyc_engine.attempt_booking(res1)
    await escrow_system.secure_hold(res1)
    print(f"Res 1 Status: {success} -> {msg}")

    res2 = Reservation(str(uuid.uuid4()), 4, base_time, base_time + timedelta(hours=1))
    print("\n[Waitlist System Processing Overlap Collision Request...]")
    success2, msg2 = await nyc_engine.attempt_booking(res2)
    print(f"Res 2 Direct Booking Attempt: {success2} -> {msg2}")
    
    if not success2:
        proposals = await NegotiationAgents.builder_propose_alternatives(nyc_engine, res2, partners=[lon_engine])
        decision = await NegotiationAgents.verifier_audit(proposals, res2)
        
        if decision:
            target_eng, target_start, target_end = decision
            res2.start_time = target_start
            res2.end_time = target_end
            
            final_success, final_msg = await target_eng.attempt_booking(res2)
            local_start = res2.start_time.astimezone(target_eng.tz)
            print(f"[Agent Success] Reallocated Res 2 to Venue Node: {target_eng.location_id} at {local_start.strftime('%I:%M %p')}. Status: {final_msg}")

    # 👇 ENSURE THESE TWO LINES ARE NOT ACCIDENTALLY INDENTED INSIDE THE "if decision" BLOCK 👇
    #await escrow_system.execute_clock_monitor(nyc_engine, res1)
    #await CentralizedAuditor.global_sanity_check([nyc_engine, lon_engine])
        clock_task = asyncio.create_task(escrow_system.execute_clock_monitor(nyc_engine, res1))
    
    # Yield control for a fraction of a second to let the background task register and process
    await asyncio.sleep(0.1)
    
    # Run the continuous global state consistency auditor check
    await CentralizedAuditor.global_sanity_check([nyc_engine, lon_engine])
    
    # Clean up the background task gracefully
    await clock_task

# THIS BLOCK MUST TOUCH THE FAR LEFT WALL WITH ZERO LEADING SPACES
if __name__ == "__main__":
    print("!!! INITIATING CORE SIMULATION LEDGER !!!")
    asyncio.run(main())
