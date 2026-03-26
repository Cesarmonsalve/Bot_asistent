import requests

token = "MTQ4NjQ5NzI5Mjg4NTI5OTI1Mg.G9leV8.qNUVhexRI8WG_wTn8gQVtWmUuw4UQZWKlhcUxM"
guild_id = "1486498876503494707"

headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
print("Testing Guild...")
r = requests.get(f"https://discord.com/api/v10/guilds/{guild_id}?with_counts=true", headers=headers)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")

print("\nTesting Channels...")
r2 = requests.get(f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers=headers)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.text[:200]}")
