import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from database import db, create_document, get_documents
from schemas import Waitlist

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# -------------------- Waitlist API --------------------

class WaitlistCreate(Waitlist):
    pass

@app.post("/waitlist")
def create_waitlist_entry(payload: WaitlistCreate):
    """Create a waitlist entry in MongoDB"""
    try:
        new_id = create_document("waitlist", payload)
        return {"id": new_id, "message": "Thanks for joining the waitlist!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/waitlist/count")
def get_waitlist_count():
    """Return the total number of waitlist entries"""
    try:
        if db is None:
            raise Exception("Database not available")
        count = db["waitlist"].count_documents({})
        return {"count": int(count)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/waitlist/recent")
def get_recent_waitlist(limit: int = 5):
    """Return recent waitlist entries (anonymized emails)"""
    try:
        docs = get_documents("waitlist", {}, limit)
        # Anonymize emails for frontend display
        def mask(email: Optional[str]):
            if not email or "@" not in email:
                return "hidden"
            name, domain = email.split("@", 1)
            if len(name) <= 2:
                masked = name[0] + "*"
            else:
                masked = name[0] + "*" * (len(name) - 2) + name[-1]
            return f"{masked}@{domain}"
        sanitized = [
            {
                "email": mask(doc.get("email")),
                "name": doc.get("name", "Friend"),
                "created_at": doc.get("created_at")
            }
            for doc in docs
        ]
        return {"items": sanitized}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
