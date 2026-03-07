import { NextRequest, NextResponse } from "next/server";
import { ensureSeedData } from "@/lib/bootstrap";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
  const { familyBook } = await ensureSeedData();
  const bookId = request.nextUrl.searchParams.get("bookId") ?? familyBook.id;

  const allocations = await prisma.salaryAllocation.findMany({
    where: { bookId },
    include: { items: true, book: true },
    orderBy: { month: "desc" },
  });

  const data = allocations.map((allocation) => ({
    ...allocation,
    salaryAmount: Number(allocation.salaryAmount),
    items: allocation.items.map((item) => ({ ...item, amount: Number(item.amount) })),
  }));

  return NextResponse.json({ allocations: data });
}

export async function POST(request: NextRequest) {
  const { familyBook } = await ensureSeedData();
  const body = await request.json();

  const bookId = String(body.bookId ?? familyBook.id);
  const month = String(body.month ?? "");
  const salaryAmount = Number(body.salaryAmount);
  const note = body.note ? String(body.note) : null;
  const items = Array.isArray(body.items) ? body.items : [];

  if (!month || Number.isNaN(salaryAmount) || salaryAmount < 0) {
    return NextResponse.json({ error: "参数不合法" }, { status: 400 });
  }

  const mappedItems = items
    .filter((item: { itemName?: string; amount?: number }) => item.itemName)
    .map((item: { itemName: string; amount: number; note?: string }) => ({
      itemName: String(item.itemName),
      amount: Number(item.amount || 0),
      note: item.note ? String(item.note) : null,
    }));

  const upserted = await prisma.salaryAllocation.upsert({
    where: {
      bookId_month: {
        bookId,
        month,
      },
    },
    update: {
      salaryAmount,
      note,
      items: {
        deleteMany: {},
        create: mappedItems,
      },
    },
    create: {
      bookId,
      month,
      salaryAmount,
      note,
      items: {
        create: mappedItems,
      },
    },
    include: { items: true, book: true },
  });

  return NextResponse.json({
    allocation: {
      ...upserted,
      salaryAmount: Number(upserted.salaryAmount),
      items: upserted.items.map((item) => ({ ...item, amount: Number(item.amount) })),
    },
  });
}
