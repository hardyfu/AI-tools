import { NextRequest, NextResponse } from "next/server";
import { TransactionType } from "@prisma/client";
import { ensureSeedData } from "@/lib/bootstrap";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
  await ensureSeedData();
  const searchParams = request.nextUrl.searchParams;
  const bookId = searchParams.get("bookId");

  const categories = await prisma.category.findMany({
    where: {
      OR: [{ bookId: null }, ...(bookId ? [{ bookId }] : [])],
    },
    orderBy: [{ type: "asc" }, { isDefault: "desc" }, { name: "asc" }],
  });

  return NextResponse.json({ categories });
}

export async function POST(request: NextRequest) {
  await ensureSeedData();
  const body = await request.json();
  const name = String(body.name ?? "").trim();
  const type = body.type as TransactionType;
  const bookId = body.bookId ? String(body.bookId) : null;

  if (!name || ![TransactionType.income, TransactionType.expense].includes(type)) {
    return NextResponse.json({ error: "参数不合法" }, { status: 400 });
  }

  const category = await prisma.category.create({
    data: { name, type, bookId, isDefault: false },
  });

  return NextResponse.json({ category }, { status: 201 });
}
