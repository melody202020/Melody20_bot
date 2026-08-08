from services.music import MusicService
ms = MusicService()

title = "For Afghanistan هوا گرمه گرمه | خرما پزونی | شادترین آهنگ بندری 2026"
clean = ms._clean_title(title)
print("Original:", title)
print("Clean:", clean)

artist = "For Afghanistan"
query = (artist + " " + clean).strip()
print("\nSearch query:", query)
results = ms._search_soundcloud(query, limit=3)
for i, r in enumerate(results):
    print(str(i+1) + ". " + r["title"] + " - " + r["artist"])
    print("   URL: " + r["url"][:80])
