# Forge Play Store Submission Notes

Last updated: 2026-06-15

## Current Build Output

- Package name: `com.devsolanki.forge`
- App name: `Forge`
- Version code: `1`
- Version name: `1.0`
- Release bundle path after build: `android/app/build/outputs/bundle/release/app-release.aab`
- Privacy policy URL: `https://forgetrivia.online/privacy.html`
- Developer website: `https://forgetrivia.online`
- Support email: `devsolanki.works@gmail.com`

## Store Listing Draft

Short description:

```text
Create AI trivia quizzes on any topic and compete live with friends.
```

Full description:

```text
Forge is a free AI trivia game where every quiz starts with your own topic.

Type a subject, start a room, and Forge creates a fresh question set for solo practice, multiplayer battles, or team quiz nights. Play quick rounds, answer under time pressure, build streaks, and climb the leaderboard with coins and trophies.

Features:
- AI-generated trivia on almost any topic
- Solo mode for practice and score chasing
- Live multiplayer rooms with simple four-character room codes
- Team mode for group battles
- Speed scoring and streak multipliers
- Google Sign-In for saved progress
- Public leaderboards for coins and trophies

Forge is built for parties, classrooms, family game nights, and casual competitive learning. No paid packs, no subscriptions, and no pay-to-win upgrades.
```

Release notes for version 1.0:

```text
Initial Android release of Forge: AI Trivia Showdown with solo play, live multiplayer rooms, team battles, AI-generated questions, coins, trophies, and leaderboards.
```

## Play Console Setup Answers

Create app:

- App or game: Game
- Free or paid: Free
- Category: Trivia
- Contact email: `devsolanki.works@gmail.com`
- Developer website: `https://forgetrivia.online`
- Privacy policy: `https://forgetrivia.online/privacy.html`

Ads declaration:

- Current AAB: answer `No`, because the native app build does not load AdSense and no AdMob SDK is integrated yet.
- Future AdMob build: change to `Yes` after adding AdMob or any in-app ads.

Target audience:

- Recommended target age: 13+
- Not primarily directed at children.
- Do not opt into Designed for Families unless the app is rebuilt and reviewed specifically for child-directed requirements.

Content rating:

- Category: Game
- Violence: none
- Sexual content: none
- Gambling: no gambling and no real-money wagering
- User-generated content: players enter display names and quiz topics
- Online interaction: yes, multiplayer rooms and player names are visible to other room participants

Sign-in details for reviewers:

```text
The app can be opened without a special test account. Google Sign-In is used for saved coins, trophies, multiplayer economy, and leaderboard sync. Reviewers can use any normal Google account. To test: open the app, sign in with Google, enter a display name, start Solo Play, choose a topic such as "general knowledge", and complete the quiz.
```

## Data Safety Draft

Data collected:

- Personal info: name, email address, profile picture, Google account ID when using Google Sign-In.
- User IDs: Google account ID for progress and leaderboard sync.
- App activity: game scores, answer counts, coins, trophies, rooms joined, and leaderboard entries.
- User-generated content: display name and quiz topic text entered by users.

Data shared:

- Quiz topic text is sent to Google Gemini API to generate questions.
- Google Sign-In uses Google authentication services.
- Leaderboard and progress data is stored in Supabase.
- Website hosting and logs are handled by Vercel for web pages.

Purpose:

- App functionality
- Account management
- Leaderboards and saved progress
- Fraud prevention and abuse prevention
- Analytics or diagnostics if added later

Security practices:

- Data is encrypted in transit through HTTPS/WSS.
- Users can request data deletion by emailing `devsolanki.works@gmail.com`.
- No real-money purchases, loot boxes, or paid currency are currently present.

## Closed Testing Requirement

For new personal Google Play developer accounts created after 2023-11-13, Google requires a closed test before production access:

- At least 12 testers
- Testers opted in continuously for at least 14 days
- Apply for production access after the test
- Keep notes about tester feedback, bugs fixed, and why the app is ready

## App-ads.txt

The website now includes:

- `https://forgetrivia.online/app-ads.txt`
- `https://forgetrivia.online/ads.txt`

When an AdMob account is created, verify the publisher ID snippet in AdMob and replace `app-ads.txt` if AdMob gives a different personalized line.

## Required Graphics Still Needed

Create these in Play Console before production:

- App icon: 512 x 512 PNG
- Feature graphic: 1024 x 500 PNG/JPG
- Phone screenshots: at least 2, recommended 4 to 8
- Optional tablet screenshots if targeting tablets

Suggested screenshot set:

1. Landing or home screen
2. Topic and difficulty setup
3. Live question screen
4. Results and leaderboard screen
5. Team mode lobby
