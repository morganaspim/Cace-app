# CACE Open Problems Toolkit

Status: executable research-navigation feature design. Problem cards and AI Play are not proof evidence.

The toolkit provides an offline-first, date-stamped catalog of major open/solved research problems. V1 seeds the seven Clay Millennium Prize Problems using a 2026-09-19 status snapshot: six open and Poincare solved.

Key behavior:

- search/filter problem cards;
- import a card to the scientific canvas as `research.open_problem`;
- Play applies non-authoritative heartbeat research-interest and sends a bounded canvas/problem context packet to the loopback-only local AI;
- custom JSON catalogs are strict-data imports only and cannot execute code or set verification state;
- problem nodes deliberately emit no VerificationRecord objects;
- source URL, authority, status and last-verified date remain visible;
- solved problems remain browsable for methodological study.

Future catalogs can cover physics, chemistry, biology, astronomy, materials and other fields using domain-appropriate authorities.
