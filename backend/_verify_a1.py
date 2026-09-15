"""Scratch verification for Stage A1 (ownership-scoped seeding). Deleted after use."""

import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./_verify_a1.db"
os.environ["MQTT_BROKER"] = ""
os.environ["DEBUG"] = "false"

import httpx  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.db.session import Base, get_db  # noqa: E402
from app.models.command import CommandLog  # noqa: E402
from app.models.device import Device  # noqa: E402
from app.models.room import Room  # noqa: E402
from app.models.user import User  # noqa: E402
from main import app  # noqa: E402

VERIFY_URL = "sqlite+aiosqlite:///./_verify_a1.db"
engine = create_async_engine(VERIFY_URL)
VerifySession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
FAILURES: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(("  OK   " if cond else "  FAIL ") + label + (f"  -> {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(label)


async def override_get_db():
    async with VerifySession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def register_and_login(c: httpx.AsyncClient, email: str) -> dict[str, str]:
    r = await c.post("/api/v1/auth/register", json={"email": email, "password": "passw0rd1", "full_name": email})
    assert r.status_code in (200, 201), r.text
    r = await c.post("/api/v1/auth/login", data={"username": email, "password": "passw0rd1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        ha = await register_and_login(c, "ownerA@example.com")
        hb = await register_and_login(c, "ownerB@example.com")

        print("\n[A] user A seeds")
        sa = await c.post("/api/v1/system/seed", headers=ha)
        check("A seed 200", sa.status_code == 200, sa.text)
        check("A got 4 rooms", sa.json()["rooms_count"] == 4, sa.text)
        check("A got 13 devices", sa.json()["devices_count"] == 13, sa.text)

        print("\n[B] user B seeds (must NOT steal A's rooms)")
        sb = await c.post("/api/v1/system/seed", headers=hb)
        check("B seed 200", sb.status_code == 200, sb.text)
        check("B got 4 rooms", sb.json()["rooms_count"] == 4, sb.text)
        check("B got 13 devices", sb.json()["devices_count"] == 13, sb.text)

        ra = (await c.get("/api/v1/rooms", headers=ha)).json()
        rb = (await c.get("/api/v1/rooms", headers=hb)).json()
        slugs_a = sorted(i["slug"] for i in ra["items"])
        slugs_b = sorted(i["slug"] for i in rb["items"])
        print(f"  A slugs: {slugs_a}")
        print(f"  B slugs: {slugs_b}")
        check("A keeps default slugs", slugs_a == ["kamar", "ruang-rapat", "ruang-tamu", "studio"], str(slugs_a))
        check("B got disambiguated slugs", all(s.endswith("-2") for s in slugs_b), str(slugs_b))
        check("A still has 4 rooms after B seeded", ra["total"] == 4, str(ra["total"]))
        check("B has 4 rooms", rb["total"] == 4, str(rb["total"]))
        check("no slug overlap", not (set(slugs_a) & set(slugs_b)))

        print("\n[C] device ids")
        async with VerifySession() as db:
            rows = (await db.execute(
                select(Device.device_id, Room.slug, Room.owner_id)
                .join(Room, Room.id == Device.room_id).order_by(Room.slug, Device.device_id)
            )).all()
        ids_a = sorted(r[0] for r in rows if r[1] in slugs_a)
        ids_b = sorted(r[0] for r in rows if r[1] in slugs_b)
        print(f"  A device_ids: {ids_a}")
        print(f"  B device_ids: {ids_b}")
        check("A keeps canonical device_ids", "dev-km-1" in ids_a, str(ids_a))
        check("B got disambiguated device_ids", "dev-km-1" not in ids_b and "dev-km-1-2" in ids_b, str(ids_b))
        check("device_id sets disjoint", not (set(ids_a) & set(ids_b)))
        check("13 devices each", len(ids_a) == 13 and len(ids_b) == 13, f"{len(ids_a)}/{len(ids_b)}")

        print("\n[D] B cannot command A's device via REST")
        cmd = await c.post("/api/v1/commands/dev-km-1", headers=hb, json={"action": "turn_on"})
        print(f"  status={cmd.status_code} (404 expected only AFTER A3/A4 owner plumbing)")
        check("B command on A's device is not 200", cmd.status_code != 200, cmd.text)

        print("\n[E] POST /rooms with a slug owned by another user")
        newroom = await c.post("/api/v1/rooms", headers=hb, json={
            "name": "Kamar", "slug": "kamar", "room_type": "bedroom", "icon": "X", "description": "dup"})
        check("create with colliding slug succeeds", newroom.status_code == 201, newroom.text)
        if newroom.status_code == 201:
            got = newroom.json()["slug"]
            check("slug disambiguated", got != "kamar" and got.startswith("kamar"), got)

        dup = await c.post("/api/v1/rooms", headers=hb, json={
            "name": "Kamar", "slug": got if newroom.status_code == 201 else "kamar",
            "room_type": "bedroom", "icon": "X", "description": "dup"})
        check("same-user duplicate slug still 409", dup.status_code == 409, dup.text)

        print("\n[F] idempotent re-seed for A")
        sa2 = await c.post("/api/v1/system/seed", headers=ha)
        check("re-seed creates nothing new", sa2.json()["rooms_count"] == 0 and sa2.json()["devices_count"] == 0, sa2.text)
        ra2 = (await c.get("/api/v1/rooms", headers=ha)).json()
        check("A still 4 rooms", ra2["total"] == 4, str(ra2["total"]))

        print("\n[G] reset only wipes the caller's data")
        resb = await c.post("/api/v1/system/reset", headers=hb)
        check("B reset 200", resb.status_code == 200, resb.text)
        check("B reset re-created 4 rooms", resb.json()["rooms_count"] == 4, resb.text)
        async with VerifySession() as db:
            a_rooms = (await db.execute(select(Room.slug).where(Room.slug.in_(slugs_a)))).scalars().all()
        check("A rooms survived B's reset", len(a_rooms) == 4, str(a_rooms))

        print("\n[H] room CRUD lifecycle via room_manager")
        cr = await c.post("/api/v1/rooms", headers=ha, json={
            "name": "Garage", "slug": "garage", "room_type": "garage", "icon": "fa-car", "description": "test"})
        check("create room 201", cr.status_code == 201, cr.text)
        garage = cr.json()
        check("create returns id/slug", bool(garage.get("id")) and garage.get("slug") == "garage", str(garage))
        check("create counts zero", garage.get("total_devices_count") == 0, str(garage))

        gid = garage["id"]
        add_dev = await c.post("/api/v1/devices", headers=ha, json={
            "device_id": "dev-gar-1", "name": "Lampu Garage", "device_type": "light", "room_id": gid})
        check("add device to new room", add_dev.status_code in (200, 201), add_dev.text)

        one = await c.get(f"/api/v1/rooms/{gid}", headers=ha)
        check("get room shows 1 device", one.status_code == 200 and one.json()["total_devices_count"] == 1, one.text)

        pa = await c.patch(f"/api/v1/rooms/{gid}", headers=ha, json={"name": "Garasi", "icon": "fa-warehouse"})
        check("patch room 200", pa.status_code == 200, pa.text)
        check("patch renamed", pa.json()["name"] == "Garasi", pa.text)
        check("patch kept slug (MQTT key)", pa.json()["slug"] == "garage", pa.text)
        check("patch kept device count", pa.json()["total_devices_count"] == 1, pa.text)

        de = await c.delete(f"/api/v1/rooms/{gid}", headers=ha)
        check("delete room 200", de.status_code == 200, de.text)
        async with VerifySession() as db:
            leftover = (await db.execute(select(Device.device_id).where(Device.device_id == "dev-gar-1"))).scalars().all()
        check("delete cascaded to devices", leftover == [], str(leftover))
        check("deleted room 404", (await c.get(f"/api/v1/rooms/{gid}", headers=ha)).status_code == 404)

        print("\n[I] B cannot touch A's rooms")
        a_room_id = next(i["id"] for i in ra["items"] if i["slug"] == "kamar")
        check("B get A's room -> 404", (await c.get(f"/api/v1/rooms/{a_room_id}", headers=hb)).status_code == 404)
        check("B patch A's room -> 404",
              (await c.patch(f"/api/v1/rooms/{a_room_id}", headers=hb, json={"name": "pwned"})).status_code == 404)
        check("B delete A's room -> 404", (await c.delete(f"/api/v1/rooms/{a_room_id}", headers=hb)).status_code == 404)
        still = await c.get(f"/api/v1/rooms/{a_room_id}", headers=ha)
        check("A's room intact", still.status_code == 200 and still.json()["name"] != "pwned", still.text)

        print("\n[J] AI path: owner scoping inside _execute_function")
        from app.api.v1.endpoints.chat import _execute_function  # noqa: E402

        async with VerifySession() as db:
            aid = (await db.execute(select(User.id).where(User.email == "ownerA@example.com"))).scalar_one()
            bid = (await db.execute(select(User.id).where(User.email == "ownerB@example.com"))).scalar_one()
            state_before = (await db.execute(select(Device.state).where(Device.device_id == "dev-km-1"))).scalar_one()
            logs_before = (await db.execute(
                select(func.count()).select_from(CommandLog).where(CommandLog.device_id == "dev-km-1")
            )).scalar_one()

            cross = await _execute_function(
                "control_device", {"device_id": "dev-km-1", "action": "turn_on"}, db, owner_id=bid
            )
            check("B via AI cannot reach A's device", cross.get("success") is False, str(cross))
            await db.rollback()

            unscoped = await _execute_function(
                "control_device", {"device_id": "dev-km-1", "action": "turn_on"}, db, owner_id=None
            )
            check("unscoped mutation refused", unscoped.get("success") is False
                  and "refused" in str(unscoped.get("error", "")), str(unscoped))

            own = await _execute_function(
                "control_device", {"device_id": "dev-km-1-2", "action": "turn_on"}, db, owner_id=bid
            )
            check("B can still control own device", own.get("success") is True, str(own))
            check("AI result carries changes", bool(own.get("changes")), str(own))
            await db.commit()

            state_after = (await db.execute(select(Device.state).where(Device.device_id == "dev-km-1"))).scalar_one()
            logs_after = (await db.execute(
                select(func.count()).select_from(CommandLog).where(CommandLog.device_id == "dev-km-1")
            )).scalar_one()
            a_rooms_after = (await db.execute(select(func.count()).select_from(Room).where(Room.owner_id == aid))).scalar_one()
        check("A's device state unchanged", state_after == state_before, f"{state_before} -> {state_after}")
        check("no CommandLog written for A's device", logs_after == logs_before, f"{logs_before} -> {logs_after}")
        check("A's room count unchanged", a_rooms_after == 4, str(a_rooms_after))

    app.dependency_overrides.clear()
    await engine.dispose()
    print("\n" + ("ALL CHECKS PASSED" if not FAILURES else f"FAILURES: {FAILURES}"))


asyncio.run(main())
