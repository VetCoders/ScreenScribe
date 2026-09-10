# TODOs dla Moniki

## Summary
- Najważniejsze tematy do poprawy wynikające z samych text‑findings:
- 1) Uspójnienie i uspokojenie UI (cienie, spójność elementów list i tooltipów).
- 2) Poprawa czytelności i zrozumiałości komunikatów/oznaczeń (gwiazdki, obowiązkowość pól, błędy).
- 3) Krytyczne poprawki logiki wyszukiwania adresu (ZIP‑first, podpowiedzi, kropka w adresie).
- 4) Stabilność i zachowanie przy awarii bootstrapa (nie blokować wejścia).
- 5) Usunięcie mylących elementów przed wydaniem ("use address search").

## Screen_Recording_2026-01-29_at_10.49.59

- [ ] [00:32] linki na termsach, na GDPR, na Terms of Service, GDPR i na Data Processing Agreement ... dużo mniej cieniowane, mniej wystające
- [ ] [01:10] Observed All Required też powinno się nam nie wystawać aż tak mocno, te cienie są zbyt wielkie w mojej ocenie
- [ ] [01:22] kolory czcionek tutaj te gwiazdki przy konsentach są nieczytelne
- [ ] [01:34] secure access to the application nie jest nigdzie nie ma nigdzie informacji czy to jest obowiązkowe czy nie
- [ ] [02:07] Bootstrap będzie zepsuty ze względu na to, że nie mam EDWA
- [ ] [02:45] gdybyśmy mogli zamienić te ostrzeżenia, tutaj jest surowe natywne ostrzeżenie Tauri
- [ ] [03:00] fajnie by była tutaj ta czytelność przekładała się na czytelność też dla użytkownika, jeśli jakikolwiek błąd wystąpi
- [ ] [03:20] To nie może stopować wejścia do aplikacji, bo lekarz musi mieć możliwość wejścia do aplikacji w momencie, kiedy bootstrap go zawiedzie
- [ ] [03:43] informacja jest totalnie nieczytelna, czyli ta w lilii inbook jest nieczytelna
- [ ] [00:46] mniej wystające, tak żeby to się zgrywało ładnie z otoczeniem

## Screen_Recording_2026-01-29_at_10.02.21

- [ ] [01:38] troszeczkę je spłaszczył.
- [ ] [01:41] Czyli zarówno w adres suggestions list, jak i w polu, polach tych dotyczących numerów kierunkowych kraju, bym to zmienił.
- [ ] [01:55] kierunkowych kraju, bym to zmienił.
- [ ] [02:03] chociaż on jest już ujednolicony, ewentualnie żeby ujednolicić ten tooltip z podpowiedzią hasła, ale on jest myślę, że spójny i stanowi spoko element.
- [ ] [02:31] Natomiast tutaj mamy rozjazd straszny, czyli adres Suggestions List vs numery vs właśnie tooltip z hasłami. To są trzy różne światy, które warto by było ujednolicić.
- [ ] [03:02] co jest tutaj krytyczne, aczkolwiek zazwyczaj piszę w stanach od ulicy, wobec czego ja bym nie poprawiał tego, że generalnie jest tutaj błąd krytyczny.
- [ ] [03:16] logiczy, bo to jest generalnie odwrócenie wtedy logiki wyszukiwania.
- [ ] [03:26] Ja bym zmienił podpowiedź, czyli podpowiedź tutaj, czyli type postal code, city, street and number to search automatically jest błędna.
- [ ] [03:33] bo nie możemy tutaj wpisywać type postal code jako pierwszy. Musimy wpisywać ulicę, tak?
- [ ] [04:04] Kropką też nie wejdzie. Teraz.
- [ ] [04:20] No my jesteśmy niewyszukiwani.
- [ ] [05:23] Ja myślę, że lepiej można usunąć po prostu use address search przed wydaniem, żeby to nie myliło, a do tego wrócić potem, bo to myślę, że będzie do zrobienia bez problemu.
