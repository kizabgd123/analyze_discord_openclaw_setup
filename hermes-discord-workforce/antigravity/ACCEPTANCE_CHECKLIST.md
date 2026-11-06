# Acceptance checklist

Antigravity ne sme da prijavi završetak dok svaka obavezna stavka nema dokaz ili eksplicitni status BLOCKED.

## Postojeće okruženje je sačuvano

- [ ] Postojeći Hermes i Discord bot ostali su instalirani i povezani.
- [ ] Nije kreiran novi Discord bot nalog/token.
- [ ] Nisu prikazane niti kopirane tajne.
- [ ] Backup relevantnih konfiguracija postoji i putanja je navedena.
- [ ] Nije resetovana Kanban baza, memorija ili postojeći profil.

## Kanban i gateway

- [ ] Lokalna Hermes verzija zaista podržava Kanban.
- [ ] Aktivni Discord orchestrator profil ima Kanban toolset.
- [ ] Nova Discord sesija vidi ažurirani toolset, ako je to potrebno.
- [ ] Postoji samo jedan aktivni dispatcher owner.
- [ ] Gateway može da pokrene dodeljene radnike.
- [ ] Task state, parent/dependency link i handoff se čuvaju.

## Tim i skill-ovi

- [ ] Uloge profila su mapirane bez nepotrebnog dupliranja.
- [ ] Skill-ovi su instalirani u odgovarajuće profile.
- [ ] Nije prepisan postojeći skill bez pregleda i backupa.
- [ ] Orchestrator kreira kartice sa jasnim acceptance kriterijumima.
- [ ] Worker vraća rezultate i stvarne dokaze.
- [ ] Verifier koristi PASS / NEEDS_CHANGES / BLOCKED.

## Discord ponašanje

- [ ] Korisnik može da pošalje zadatak postojećem botu.
- [ ] Bot ne odgovara na svaki kanalni razgovor bez dozvole/mention-a.
- [ ] Bot ne pravi neograničenu bot-to-bot konverzaciju.
- [ ] Rezultat i terminalna notifikacija stižu u odgovarajuću Discord sesiju/thread.

## End-to-end dokaz

- [ ] Testni researcher zadatak je kreiran i izvršen.
- [ ] Verifier zadatak je zavisio od researcher zadatka.
- [ ] Verifier je potvrdio izvore/kriterijume ili dao konkretan razlog za neuspeh.
- [ ] Orchestrator je objavio objedinjeni rezultat na Discord-u.
- [ ] Izveštaj sadrži stvarne task ID-jeve, status, logove/putanje i neproverene stavke.

**Završni status:** PASS samo ako svi obavezni testovi prođu. U suprotnom PARTIAL/BLOCKED, uz konkretan dokaz.
