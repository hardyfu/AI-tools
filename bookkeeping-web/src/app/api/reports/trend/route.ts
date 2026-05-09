import { NextRequest, NextResponse } from "next/server";
import { ensureSeedData } from "@/lib/bootstrap";
import { monthRange, toMonthString } from "@/lib/date";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
  const { familyBook } = await ensureSeedData();
  const searchParams = request.nextUrl.searchParams;
  const bookId = searchParams.get("bookId") ?? familyBook.id;
  const months = Math.min(Math.max(Number(searchParams.get("months") ?? 12), 1), 24);

  const now = new Date();
  const currentMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const start = new Date(currentMonthStart.getFullYear(), currentMonthStart.getMonth() - (months - 1), 1);
  const end = new Date(currentMonthStart.getFullYear(), currentMonthStart.getMonth() + 1, 1);

  const transactions = await prisma.transaction.findMany({
    where: { bookId, date: { gte: start, lt: end } },
    select: { date: true, amount: true, type: true },
    orderBy: { date: "asc" },
  });

  const map = new Map<string, { month: string; income: number; expense: number; balance: number }>();
  for (let i = 0; i < months; i += 1) {
    const d = new Date(start.getFullYear(), start.getMonth() + i, 1);
    const month = toMonthString(d);
    map.set(month, { month, income: 0, expense: 0, balance: 0 });
  }

  for (const tx of transactions) {
    const month = toMonthString(tx.date);
    const bucket = map.get(month);
    if (!bucket) continue;
    const amount = Number(tx.amount);
    if (tx.type === "income") bucket.income += amount;
    if (tx.type === "expense") bucket.expense += amount;
  }

  const trend = Array.from(map.values()).map((item) => ({
    ...item,
    balance: item.income - item.expense,
  }));

  const month = searchParams.get("month") ?? toMonthString(now);
  const { start: monthStart, end: monthEnd } = monthRange(month);

  const [monthEndBalanceRows, monthRows] = await Promise.all([
    prisma.transaction.findMany({
      where: { bookId, date: { lt: monthEnd } },
      select: { type: true, amount: true },
    }),
    prisma.transaction.findMany({
      where: { bookId, date: { gte: monthStart, lt: monthEnd } },
      select: { type: true, amount: true },
    }),
  ]);

  let openingFundTotal = 0;
  try {
    const openingFund = await prisma.openingFund.findUnique({ where: { bookId }, include: { buckets: true } });
    const openingFundBucketTotal = (openingFund?.buckets ?? []).reduce(
      (sum, item) => sum + Number(item.amount),
      0,
    );
    openingFundTotal =
      Number(openingFund?.cashAmount ?? 0) +
      Number(openingFund?.wealthAmount ?? 0) +
      openingFundBucketTotal;
  } catch {
    openingFundTotal = 0;
  }

  let monthEndBalance = openingFundTotal;
  for (const row of monthEndBalanceRows) {
    const amount = Number(row.amount);
    monthEndBalance += row.type === "income" ? amount : -amount;
  }

  let monthIncome = 0;
  let monthExpense = 0;
  for (const row of monthRows) {
    const amount = Number(row.amount);
    if (row.type === "income") monthIncome += amount;
    if (row.type === "expense") monthExpense += amount;
  }

  return NextResponse.json({
    trend,
    monthSummary: {
      month,
      income: monthIncome,
      expense: monthExpense,
      monthBalance: monthIncome - monthExpense,
      monthEndBalance,
      openingFundTotal,
    },
  });
}
