from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from backend.database import get_user, NFT_PRIZES, get_game_history
from backend.game_logic import (
    manager, active_rooms, create_game_room, join_game_room, _get_settings
)

router = APIRouter(prefix="/api/game", tags=["game"])


class JoinRoomRequest(BaseModel):
    telegram_id: int
    room_id: Optional[str] = None
    bet: int


@router.get("/rooms")
async def list_rooms():
    rooms = []
    for rid, room in active_rooms.items():
        if room.status in ("waiting", "betting"):
            rooms.append({
                "room_id": rid,
                "player_count": len(room.players),
                "total_bank": room.get_total_bank(),
                "status": room.status,
                "time_left": room.time_left,
            })
    return {"rooms": rooms}


@router.get("/nft-prizes")
async def nft_prizes():
    return {"prizes": NFT_PRIZES}


@router.get("/history")
async def game_history(limit: int = Query(20, le=100)):
    games = await get_game_history(limit=limit)
    return {"games": games}


@router.get("/current")
async def get_current_room():
    settings = await _get_settings()
    commission_rate = int(settings.get("commission_rate", 5))
    timer = int(settings.get("game_timer", 30))
    max_p = int(settings.get("max_players", 8))
    
    for rid, room in active_rooms.items():
        if room.status in ("waiting", "betting") and len(room.players) < max_p:
            return {
                "room_id": rid,
                "room": room.to_dict(),
                "active_theme": settings.get("active_theme", "classic"),
                "chat_enabled": settings.get("chat_enabled", "1")
            }
            
    room = await create_game_room(0, commission_rate, timer)
    return {
        "room_id": room.room_id,
        "room": room.to_dict(),
        "active_theme": settings.get("active_theme", "classic"),
        "chat_enabled": settings.get("chat_enabled", "1")
    }


@router.post("/join")
async def join_game(body: JoinRoomRequest):
    user = await get_user(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Hisobingiz bloklangan")

    settings = await _get_settings()
    commission_rate = int(settings.get("commission_rate", 5))
    timer = int(settings.get("game_timer", 30))

    # Find or create room
    if body.room_id and body.room_id in active_rooms:
        room_id = body.room_id
    else:
        # Find available room or create new
        available = None
        for rid, room in active_rooms.items():
            if room.status in ("waiting", "betting"):
                max_p = int(settings.get("max_players", 8))
                if len(room.players) < max_p and not room.has_player(body.telegram_id):
                    available = rid
                    break
        if available:
            room_id = available
        else:
            room = await create_game_room(body.telegram_id, commission_rate, timer)
            room_id = room.room_id

    success, msg = await join_game_room(room_id, user, body.bet)
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    room = active_rooms[room_id]
    await manager.broadcast(room_id, {
        "action": "player_joined",
        **room.to_dict()
    })

    return {"success": True, "room_id": room_id, "room": room.to_dict()}


@router.get("/room/{room_id}")
async def get_room(room_id: str):
    room = active_rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Xona topilmadi")
    return room.to_dict()


@router.websocket("/ws/{room_id}")
async def game_websocket(websocket: WebSocket, room_id: str, telegram_id: int = Query(...)):
    user = await get_user(telegram_id)
    if not user or user.get("approval_status") != "approved" or user.get("is_banned"):
        await websocket.accept()
        await websocket.close(code=4003, reason="Tasdiqlanmagan")
        return
        
    await manager.connect(websocket, room_id, telegram_id)
    try:
        room = active_rooms.get(room_id)
        if room:
            await websocket.send_json({
                "action": "connected",
                **room.to_dict()
            })
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "ping":
                await websocket.send_json({"action": "pong"})
            elif action == "chat":
                room = active_rooms.get(room_id)
                if room:
                    await manager.broadcast(room_id, {
                        "action": "chat",
                        "telegram_id": telegram_id,
                        "message": data.get("message", "")[:200],
                    })
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id, telegram_id)
        room = active_rooms.get(room_id)
        if room:
            await manager.broadcast(room_id, {
                "action": "player_left",
                "telegram_id": telegram_id,
            })
