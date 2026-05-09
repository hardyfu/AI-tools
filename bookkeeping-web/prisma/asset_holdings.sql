CREATE TABLE IF NOT EXISTS "AssetHolding" (
  "id" TEXT NOT NULL PRIMARY KEY,
  "bookId" TEXT NOT NULL,
  "type" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "quantity" DECIMAL NOT NULL DEFAULT 0,
  "costAmount" DECIMAL NOT NULL DEFAULT 0,
  "currentPrice" DECIMAL NOT NULL DEFAULT 0,
  "currentValue" DECIMAL NOT NULL DEFAULT 0,
  "note" TEXT,
  "isActive" BOOLEAN NOT NULL DEFAULT true,
  "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" DATETIME NOT NULL,
  CONSTRAINT "AssetHolding_bookId_fkey" FOREIGN KEY ("bookId") REFERENCES "Book" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS "AssetHolding_bookId_type_idx" ON "AssetHolding"("bookId", "type");

CREATE TABLE IF NOT EXISTS "AssetTrade" (
  "id" TEXT NOT NULL PRIMARY KEY,
  "holdingId" TEXT NOT NULL,
  "tradeType" TEXT NOT NULL,
  "date" DATETIME NOT NULL,
  "quantity" DECIMAL NOT NULL,
  "price" DECIMAL NOT NULL DEFAULT 0,
  "amount" DECIMAL NOT NULL,
  "fee" DECIMAL NOT NULL DEFAULT 0,
  "note" TEXT,
  "relationKey" TEXT,
  "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "AssetTrade_holdingId_fkey" FOREIGN KEY ("holdingId") REFERENCES "AssetHolding" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS "AssetTrade_holdingId_date_idx" ON "AssetTrade"("holdingId", "date");
CREATE INDEX IF NOT EXISTS "AssetTrade_relationKey_idx" ON "AssetTrade"("relationKey");
