# Zuerst lesen wir die Datei

with open ('text1.txt', "r") as file:
    data = file.readlines()

schritte = []

for zeile in data:
    zahl = int(zeile[1:])
    if zeile[0] == 'L':
        zahl *= -1
    schritte.append(zahl)


#Teil 1 des Rätsels

position = 50
zaehler = 0
for schritt in schritte:
    position += schritt
    position %= 100
    if position == 0:
        zaehler += 1

print(zaehler)

#Teil 2 des Rätsels

position = 50
zaehler = 0
ueberschritten = 0
for schritt in schritte:
    position += schritt
    if position  100:
