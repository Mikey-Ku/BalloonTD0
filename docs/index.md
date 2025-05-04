

<link rel="stylesheet" href="style.css">

<header class="site-header">
  <h1>Balloons Tower Defense</h1>
  <nav class="site-nav">
    <a href="#about">About</a>
    <a href="#features">Features</a>
    <a href="#gameplay">Gameplay</a>
    <a href="#installation">Installation</a>
    <a href="#Attributions">Attributions</a>
  </nav>
</header>

<hr />

## About {#about}

A simple tower-defense game built in **Python** using **Pygame**, inspired by Ninja Kiwi’s Bloons TD. Strategically place and upgrade towers to defend against waves of colorful balloons racing along custom paths!

<hr />

## Features {#features}

- **Four tower types**, each with unique behavior :

<div class="tower-grid">
  <figure class="tower-item">
    <img src="screenshots/monkey_images/dart_monkey.png" alt="Dart Monkey">
    <figcaption>Dart Monkey</figcaption>
  </figure>
  <figure class="tower-item">
    <img src="screenshots/monkey_images/sniper_monkey.png" alt="Sniper Monkey">
    <figcaption>Sniper Monkey</figcaption>
  </figure>
  <figure class="tower-item">
    <img src="screenshots/monkey_images/tac_tower.png" alt="Tac Shooter">
    <figcaption>Tac Shooter</figcaption>
  </figure>
  <figure class="tower-item">
    <img src="screenshots/monkey_images/super_monkey.png" alt="Super Monkey">
    <figcaption>Super Monkey</figcaption>
  </figure>
</div>

- **Six balloon enemy types** with increasing toughness :

<div class="balloon-grid">
  <figure class="balloon-item">
    <img src="screenshots/balloon_images/red_balloon.png" alt="Red Balloon">
    <figcaption>Red Balloon</figcaption>
  </figure>
  <figure class="balloon-item">
    <img src="screenshots/balloon_images/blue_balloon.png" alt="Blue Balloon">
    <figcaption>Blue Balloon</figcaption>
  </figure>
  <figure class="balloon-item">
    <img src="screenshots/balloon_images/green_balloon.png" alt="Green Balloon">
    <figcaption>Green Balloon</figcaption>
  </figure>
  <figure class="balloon-item">
    <img src="screenshots/balloon_images/yellow_balloon.png" alt="Yellow Balloon">
    <figcaption>Yellow Balloon</figcaption>
  </figure>
  <figure class="balloon-item">
    <img src="screenshots/balloon_images/pink_balloon.png" alt="Pink Balloon">
    <figcaption>Pink Balloon</figcaption>
  </figure>
  <figure class="balloon-item">
    <img src="screenshots/balloon_images/moab.png" alt="MOAB Boss">
    <figcaption>MOAB Boss</figcaption>
  </figure>
</div>


- **20 configurable rounds** with varying spawn patterns  
- **Interactive UI**: place, upgrade, sell towers & toggle game speed  

<hr />

## Gameplay {#gameplay}

Watch the action in motion!  
[▶️ Watch gameplay video](https://youtu.be/<your-video-id>)

<div class="screenshot-grid">
  <!-- Screenshot 1 -->
  ![Wave 1 Setup](path/to/screenshot1.png)  
  *Early-game setup*

  <!-- Screenshot 2 -->
  ![MOAB Incoming](path/to/screenshot2.png)  
  *Mid-game boss wave*

  <!-- Screenshot 3 -->
  ![Late Game](path/to/screenshot3.png)  
  *Late-game chaos*
</div>

<hr />

## Installation {#installation}

```bash
git clone https://github.com/<your-username>/balloon-td.git
cd balloon-td
pip install -r requirements.txt
python main.py

## Attributions {#attributions}

### Game Concept
We gratefully acknowledge **Ninja Kiwi** for the original *Bloons Tower Defense* concept, which served as our inspiration whenever we debated how to implement core mechanics. For more info:  

[https://ninjakiwi.com/Games/Mobile/Bloons-Tower-Defense-5.html](https://ninjakiwi.com/Games/Mobile/Bloons-Tower-Defense-5.html)

### Author Credits
- **Michael Ku Jr.** — [https://github.com/Mikey-Ku](https://github.com/Mikey-Ku) 
- **Hong Yi Zhang** — [https://github.com/tastychez](https://github.com/tastychez)  
- **Jackson Gamache** — [https://github.com/jackson-gamache](https://github.com/jackson-gamache)
