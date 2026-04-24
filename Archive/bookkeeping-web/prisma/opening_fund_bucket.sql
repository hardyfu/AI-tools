CREATE TABLE IF NOT EXISTS "OpeningFundBucket" (
  "id" TEXT NOT NULL PRIMARY KEY,
  "openingFundId" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "amount" DECIMAL NOT NULL DEFAULT 0,
  "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" DATETIME NOT NULL,
  CONSTRAINT "OpeningFundBucket_openingFundId_fkey" FOREIGN KEY ("openingFundId") REFERENCES "OpeningFund" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS "OpeningFundBucket_openingFundId_idx" ON "OpeningFundBucket"("openingFundId");
