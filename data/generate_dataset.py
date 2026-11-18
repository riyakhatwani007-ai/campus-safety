"""Builds a STARTER dataset (data/emergency_data.csv).
It is synthetic: base sentences x prefixes/suffixes x random typos.
Add your OWN real-style messages to the CSV to make the model more credible."""
import csv, random, os

random.seed(42)

BASE = {
 "medical": [
  ("my friend fainted and is not responding","high"),("he is not breathing please help","high"),
  ("someone is having chest pain and sweating a lot","high"),("she collapsed in the corridor","high"),
  ("heavy bleeding from his head","high"),("a student is having a seizure","high"),
  ("i am having an asthma attack and have no inhaler","high"),("allergic reaction, face is swelling","high"),
  ("mere dost ko chakkar aa raha hai aur vo behosh ho gaya","high"),("saans lene me dikkat ho rahi hai","high"),
  ("i have a bad headache and feel dizzy","low"),("mujhe bukhar hai aur sar dard ho raha hai","low"),
  ("i feel feverish and have a stomach ache","low"),("food poisoning, vomiting since morning","medium"),
  ("my ankle is swollen after a fall and it hurts","medium"),("i cut my finger while cooking, bleeding a little","low"),
  ("pet me bahut dard ho raha hai aur ulti ho rahi hai","medium"),
 ],
 "fire": [
  ("there is a fire in the hostel kitchen","high"),("flames spreading on the second floor","high"),
  ("hostel me aag lag gayi hai","high"),("people trapped in the building with smoke everywhere","high"),
  ("gas cylinder leak smell in the mess","high"),("bijli ke board me spark hua aur aag lag gayi","high"),
  ("smoke coming out of the lab room","medium"),("short circuit sparks in the classroom socket","medium"),
  ("fire alarm is ringing and i smell burning","medium"),("a bike is burning in the parking","medium"),
  ("lab se dhuan nikal raha hai","medium"),("small fire in the dustbin near canteen","low"),
  ("burning smell from the ac in my room","low"),("room ke plug se jalne ki smell aa rahi hai","low"),
 ],
 "accident": [
  ("bike accident near the main gate, rider is injured","high"),("someone got hit by a vehicle on the road","high"),
  ("bus accident near the college gate","high"),("student fell from the first floor balcony","high"),
  ("gate ke paas accident ho gaya, bahut khoon aa raha hai","high"),("electric shock from the switchboard in lab","high"),
  ("lab accident, chemical spilled on his hand","high"),("a student fell from the stairs and cannot stand","medium"),
  ("two cars collided in the campus parking","medium"),("scooty se gir gaya, haath me chot lagi hai","medium"),
  ("a fan fell and injured a student in the classroom","medium"),("i slipped in the corridor and hurt my knee","low"),
  ("mera pair mud gaya football khelte hue","low"),("minor scratch after falling from my cycle","low"),
 ],
 "security": [
  ("a man with a weapon is on campus","high"),("someone is following me near the hostel at night","high"),
  ("a stranger is harassing girls near the gate","high"),("ragging happening in the hostel room","high"),
  ("mujhe koi pareshan kar raha hai, mujhe darr lag raha hai","high"),("i am being stalked and need help immediately","high"),
  ("there is a fight between students in the ground","medium"),("suspicious person roaming around the girls hostel","medium"),
  ("hostel ke bahar ladai ho rahi hai","medium"),("my phone got snatched near the bus stop","medium"),
  ("someone is threatening me on call","medium"),("koi bina permission ke hostel me ghus gaya","medium"),
  ("my laptop was stolen from the library","low"),("bike chori ho gayi parking se","low"),
 ],
 "natural_disaster": [
  ("earthquake tremors felt in the building","high"),("bhukamp aa raha hai, building hil rahi hai","high"),
  ("heavy flooding on campus, water entering ground floor","high"),("flood water rising in the hostel basement","high"),
  ("lightning struck near the playground","high"),("ceiling cracks after the earthquake","high"),
  ("strong storm, tree fell near the hostel","medium"),("cyclone warning and strong winds shaking windows","medium"),
  ("tez aandhi se ped gir gaya","medium"),("hailstorm broke windows in the lab","medium"),
  ("baarish se road par paani bhar gaya, jaana mushkil hai","low"),("roof leaking and water logging in the corridor due to rain","low"),
 ],
}

EXTRA = {
 "medical": [
  ("a girl in my class is vomiting and looks very weak","medium"),("my roommate has high fever and is shivering","medium"),
  ("he hit his head and now he is confused","high"),("i got rashes all over my body after taking a tablet","medium"),
  ("my friend is not waking up","high"),("period cramps are unbearable, need a doctor","low"),
  ("diabetic student feels shaky and sweaty, needs sugar","medium"),("tooth pain since last night, cant study","low"),
  ("meri tabiyat kharab hai, ulti aur chakkar aa rahe hain","medium"),("dost ko seene me dard ho raha hai, dil ka daura lag raha hai","high"),
  ("i think i broke my arm, it looks bent","high"),("mujhe ghabrahat ho rahi hai aur pasina aa raha hai","medium"),
 ],
 "fire": [
  ("the canteen stove caught fire and it is spreading","high"),("i can see black smoke coming from the chemistry lab","medium"),
  ("transformer blast near the gate with sparks and flames","high"),("fire extinguisher needed urgently in block c","high"),
  ("a wire is burning in the corridor","medium"),("dry grass behind the hostel caught fire","medium"),
  ("charger blast in my room and the mattress is burning","high"),("someone left the stove on and the pan is smoking","low"),
  ("kitchen me tel me aag lag gayi","high"),("generator se dhuan aur chingari nikal rahi hai","medium"),
  ("smell of gas and smoke on the third floor","high"),
 ],
 "accident": [
  ("a cyclist was knocked down by a speeding car near the library","high"),("two students collided while running, one is crying in pain","low"),
  ("auto rickshaw overturned outside the university gate","high"),("a ceiling tile fell on a student's head","medium"),
  ("someone fell in the bathroom and is lying on the floor","medium"),("a boy burnt his hand with hot oil in the mess","medium"),
  ("pole se takra gaya bike, sar me chot hai","high"),("seedhiyon se phisal gayi, ghutne me dard hai","low"),
  ("lab me test tube toot gaya aur haath kat gaya","medium"),("road par truck ne ek student ko takkar maar di","high"),
  ("playground me khelte hue ladke ka pair toot gaya","medium"),
 ],
 "security": [
  ("two unknown men entered the girls hostel and refuse to leave","high"),("someone is recording girls in the washroom with a phone","high"),
  ("seniors are forcing freshers to do things against their will","high"),("an unknown person is asking for my room number","medium"),
  ("the cctv camera near the gate is broken","low"),("drunk men are making trouble outside the campus","medium"),
  ("my bag was taken from the classroom","low"),("someone is sending me threatening messages online","medium"),
  ("raat ko koi mere room ka darwaza khatkhata raha hai","high"),("ek ladka mujhe roz peecha karta hai","high"),
  ("canteen me jhagda ho gaya, chaaku nikala","high"),("meri cycle chori ho gayi","low"),
 ],
 "natural_disaster": [
  ("the ground is shaking and everyone is running outside","high"),("water has entered the library after continuous rain","medium"),
  ("a big branch fell on the road after the storm and blocked it","medium"),("heavy thunderstorm, students stuck in the lab","medium"),
  ("river level rising near the campus after dam water release","high"),("extreme heat wave, many students feeling dizzy","medium"),
  ("thick fog and zero visibility on the campus road","low"),("tez baarish me hostel ki chhat tapak rahi hai","low"),
  ("zameen hil rahi hai, sab bahar bhaago","high"),("nadi ka pani campus ki taraf badh raha hai","high"),
  ("olavrishti se gaadi ke sheeshe toot gaye","medium"),
 ],
}
for _c, _items in EXTRA.items():
    BASE[_c] += _items

PREFIX = ["", "", "help! ", "please help, ", "urgent: ", "bhai ", "sir ", "emergency - ", "madam "]
SUFFIX = ["", "", " please come fast", " near the hostel", " in the library", " jaldi aao", " at the main gate", " in the lab", " right now"]

def typo(s):
    if random.random() < 0.35 and len(s) > 6:
        i = random.randrange(1, len(s) - 2)
        s = s[:i] + s[i+1] + s[i] + s[i+2:] if random.random() < 0.5 else s[:i] + s[i+1:]
    return s

rows, seen, base_id = [], set(), 0
for cat, items in BASE.items():
    for text, sev in items:
        base_id += 1
        for _ in range(7):
            t = typo((random.choice(PREFIX) + text + random.choice(SUFFIX)).strip())
            if t not in seen:
                seen.add(t); rows.append((t, cat, sev, base_id))
random.shuffle(rows)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emergency_data.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["text", "category", "severity", "base_id"]); w.writerows(rows)
print(f"Wrote {len(rows)} rows to {out}")
