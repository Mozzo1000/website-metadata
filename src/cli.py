from main import Metadata

p = Metadata("https://google.com")
print(p.title)
for i in p.icons:
    p.save()