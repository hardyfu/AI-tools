import { NextResponse } from "next/server";
import { ensureSeedData } from "@/lib/bootstrap";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export async function GET() {
  await ensureSeedData();
  const books = await prisma.book.findMany({ orderBy: { createdAt: "asc" } });
  return NextResponse.json({ books });
}
