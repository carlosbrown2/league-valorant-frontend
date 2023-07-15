CREATE TABLE "matches" (
  "match_id" varchar,
  "Date" timestamp,
  "Game_Length" float,
  "Rounds" int,
  "Map" varchar,
  "Mode" varchar,
  "Red_Score" int,
  "Blue_Score" int,
  "Red_Roster" varchar,
  "Blue_Roster" varchar,
  "Home_Team" varchar,
  "Outcome" varchar,
  PRIMARY KEY ("match_id")
);

CREATE TABLE "player_stats" (
  "match_id" varchar,
  "puuid" varchar,
  "name" varchar,
  "tag" varchar,
  "agent" varchar,
  "playtime" int,
  "kills" int,
  "deaths" int,
  "assists" int,
  "acs" int,
  "bodyshots" int,
  "headshots" int,
  "legshots" int,
  "c_cast" int,
  "q_cast" int,
  "e_cast" int,
  "x_cast" int,
  PRIMARY KEY ("match_id")
);

CREATE TABLE "matches_player_stats" (
  "matches_match_id" varchar NOT NULL,
  "player_stats_match_id" varchar NOT NULL,
  PRIMARY KEY ("matches_match_id", "player_stats_match_id")
);

ALTER TABLE "matches_player_stats" ADD FOREIGN KEY ("matches_match_id") REFERENCES "matches" ("match_id");

ALTER TABLE "matches_player_stats" ADD FOREIGN KEY ("player_stats_match_id") REFERENCES "player_stats" ("match_id");
