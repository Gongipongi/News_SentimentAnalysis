CREATE TABLE "cards" (
    "id" INTEGER,
    "name" TEXT NOT NULL,
    PRIMARY KEY("id") 

);

CREATE TABLE "stations" (
    "id" INTEGER,
    "name" TEXT NOT NULL UNIQUE,
    "line" TEXT NOT NULL UNIQUE,
    PRIMARY KEY("id")
);

CREATE TABLE "swipes" (
    "card_id" INTEGER,
    "station_id" INTEGER,
    "type" TEXT NOT NULL CHECK("type" IN ('enter', 'exit', 'deposit')),
    "datetime" NUMERIC, NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "amount" NUMERIC NOT NULL CHECK("amount" != 0),
     FOREIGN KEY("card_id") REFERENCES "cards"("id"),
     FOREIGN KEY("station_id") REFERENCES "stations"("id")
);