# Local service availability research

Use this pattern when the user wants a shortlist of real-world providers with a hard scheduling constraint such as Sunday hours.

## Evidence ladder
1. Practitioner/service page explicitly naming condition fit and treatment scope
2. Clinic contact/opening-hours page showing Sunday or weekend opening
3. Booking-directory snippet suggesting weekend appointments
4. Generic directory listing or homepage marketing copy

Do not treat (2) alone as proof that the practitioner works that day.
Do not treat (3) alone as fully confirmed availability when the booking page is dynamic or blocked.

## Condition-fit signals for podiatry
Strong matches:
- plantar fasciitis
- heel pain
- orthotics / orthotic therapy
- biomechanics / lower-limb biomechanics
- foot and ankle pain
- flat feet / overpronation
- gait concerns

## Ranking pattern
Rank candidates in this order:
1. hard constraint met (e.g. Sunday)
2. explicit condition fit
3. proximity to the user's preferred suburb
4. booking convenience / contact clarity

## Output shape
For each candidate include:
- provider name
- clinic name
- suburb/address
- phone
- Sunday hours status
- why they fit the condition
- confidence note if availability is inferred rather than explicit

## Phrasing to use
- "clinic is open Sunday, but specialist Sunday availability is not fully confirmed"
- "strongest verified nearby option"
- "best backup if you can travel a bit further"

## Anti-patterns
- claiming booking availability from a search snippet as settled fact
- saying a clinic is the 'best' without naming the evidence basis
- mixing 'nearby' and 'best fit' without showing the tradeoff
