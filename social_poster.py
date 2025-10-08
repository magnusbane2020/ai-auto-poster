import httpx, json, os
from config import CFG

# ---------- Facebook ----------
def post_facebook(message: str, image_path: str | None = None) -> str:
    page_id = CFG["FB_PAGE_ID"]
    token = CFG["FB_PAGE_ACCESS_TOKEN"]
    base = f"https://graph.facebook.com/v21.0/{page_id}"
    with httpx.Client(timeout=30) as x:
        if image_path:
            # upload photo with caption
            files = {"source": open(image_path, "rb")}
            data = {"caption": message, "access_token": token}
            r = x.post(f"{base}/photos", data=data, files=files)
        else:
            r = x.post(f"{base}/feed", data={"message": message, "access_token": token})
        r.raise_for_status()
        j = r.json()
        # Return permalink
        post_id = j.get("post_id") or j.get("id")
        if not post_id: return ""
        pr = x.get(f"https://graph.facebook.com/v21.0/{post_id}",
                   params={"fields":"permalink_url", "access_token": token}).json()
        return pr.get("permalink_url","")

# ---------- LinkedIn ----------
def post_linkedin(message: str, image_path: str | None = None) -> str:
    token = CFG["LINKEDIN_ACCESS_TOKEN"]
    owner = CFG["LINKEDIN_ORG_URN"] or CFG["LINKEDIN_PERSON_URN"]
    if not owner:
        raise RuntimeError("Set LINKEDIN_PERSON_URN or LINKEDIN_ORG_URN")
    headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version":"2.0.0", "Content-Type":"application/json"}

    with httpx.Client(timeout=40) as x:
        if image_path:
            # 1) register upload
            init = x.post("https://api.linkedin.com/v2/assets?action=registerUpload",
                          headers=headers,
                          json={
                            "registerUploadRequest":{
                              "recipes":["urn:li:digitalmediaRecipe:feedshare-image"],
                              "owner": owner,
                              "serviceRelationships":[{"relationshipType":"OWNER","identifier":"urn:li:userGeneratedContent"}]
                            }
                          }).json()
            upload_url = init["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset = init["value"]["asset"]
            # 2) upload binary
            with open(image_path,"rb") as f:
                x.put(upload_url, headers={"Authorization": f"Bearer {token}"}, content=f.read())
            # 3) post with image asset
            body = {
              "author": owner,
              "lifecycleState": "PUBLISHED",
              "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                  "shareCommentary": {"text": message},
                  "shareMediaCategory": "IMAGE",
                  "media": [{"status":"READY","media":asset}]
                }
              },
              "visibility": {"com.linkedin.ugc.MemberNetworkVisibility":"CONNECTIONS"}
            }
        else:
            # text-only
            body = {
              "author": owner,
              "lifecycleState": "PUBLISHED",
              "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                  "shareCommentary": {"text": message},
                  "shareMediaCategory": "NONE"
                }
              },
              "visibility": {"com.linkedin.ugc.MemberNetworkVisibility":"CONNECTIONS"}
            }
        r = x.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=body)
        r.raise_for_status()
        return ""  # LinkedIn doesn’t immediately return permalink; optional follow-up fetch if needed
