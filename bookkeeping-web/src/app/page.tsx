"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { currentMonth, formatCurrency, todayString } from "@/lib/ui";

type Book = { id: string; name: "child" | "family"; displayName: string };
type DashboardScope = { id: string; label: string; type: "all" | "book" };
type DateMode = "all" | "month" | "range";
type Summary = {
  income: number;
  expense: number;
  monthBalance: number;
  runningBalance: number;
  openingFundTotal: number;
};
type BreakdownItem = { categoryId: string; categoryName: string; type: string; amount: number };
type TrendItem = { month: string; income: number; expense: number; balance: number };
type AssetItem = { name: string; amount: number };
type Transaction = {
  id: string;
  date: string;
  type: "income" | "expense";
  amount: number;
  note?: string | null;
  relationKey?: string | null;
  category: { name: string };
};

const pieColors = ["#1f2937", "#475569", "#0f766e", "#a16207", "#be123c", "#0ea5e9", "#4338ca", "#64748b"];

const emptySummary: Summary = {
  income: 0,
  expense: 0,
  monthBalance: 0,
  runningBalance: 0,
  openingFundTotal: 0,
};

async function parseJson<T>(res: Response): Promise<T | null> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

function buildTrend(transactions: Transaction[]) {
  const map = new Map<string, TrendItem>();
  for (const tx of transactions) {
    const month = tx.date.slice(0, 7);
    const existing = map.get(month) ?? { month, income: 0, expense: 0, balance: 0 };
    if (tx.type === "income") existing.income += tx.amount;
    if (tx.type === "expense") existing.expense += tx.amount;
    existing.balance = existing.income - existing.expense;
    map.set(month, existing);
  }
  return Array.from(map.values())
    .sort((a, b) => a.month.localeCompare(b.month))
    .slice(-12);
}

function buildBreakdown(transactions: Transaction[]) {
  const map = new Map<string, BreakdownItem>();
  for (const tx of transactions) {
    const key = `${tx.type}:${tx.category.name}`;
    const existing = map.get(key);
    if (existing) {
      existing.amount += tx.amount;
    } else {
      map.set(key, {
        categoryId: key,
        categoryName: tx.category.name,
        type: tx.type,
        amount: tx.amount,
      });
    }
  }
  return Array.from(map.values()).sort((a, b) => b.amount - a.amount);
}

function sumByType(transactions: Transaction[]) {
  let income = 0;
  let expense = 0;
  for (const tx of transactions) {
    if (tx.type === "income") income += tx.amount;
    if (tx.type === "expense") expense += tx.amount;
  }
  return { income, expense };
}

export default function DashboardPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [scopeId, setScopeId] = useState("all");

  const [dateMode, setDateMode] = useState<DateMode>("all");
  const [month, setMonth] = useState(currentMonth());
  const [rangeStart, setRangeStart] = useState(`${new Date().getFullYear()}-01-01`);
  const [rangeEnd, setRangeEnd] = useState(todayString());

  const [summary, setSummary] = useState<Summary>({ ...emptySummary });
  const [breakdown, setBreakdown] = useState<BreakdownItem[]>([]);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [assetBreakdown, setAssetBreakdown] = useState<AssetItem[]>([]);

  const scopes = useMemo<DashboardScope[]>(() => {
    return [
      { id: "all", label: "总体", type: "all" },
      ...books.map((book): DashboardScope => ({ id: book.id, label: book.displayName, type: "book" })),
    ];
  }, [books]);

  useEffect(() => {
    const loadBooks = async () => {
      const res = await fetch("/api/books");
      const data = await res.json();
      const nextBooks = data.books as Book[];
      setBooks(nextBooks);
      setScopeId((prev) => (prev && (prev === "all" || nextBooks.some((book) => book.id === prev)) ? prev : "all"));
    };
    void loadBooks();
  }, []);

  useEffect(() => {
    if (books.length === 0) return;

    const load = async () => {
      try {
        const selected = scopes.find((item) => item.id === scopeId) ?? scopes[0];
        if (!selected) return;
        const targetBookIds = selected.type === "all" ? books.map((book) => book.id) : [selected.id];

        const paramsByMode = new URLSearchParams({ limit: "5000" });
        if (dateMode === "month") {
          paramsByMode.set("month", month);
        }
        if (dateMode === "range") {
          if (rangeStart) paramsByMode.set("dateFrom", rangeStart);
          if (rangeEnd) paramsByMode.set("dateTo", rangeEnd);
        }

        const txResponses = await Promise.all(
          targetBookIds.map((bookId) => {
            const params = new URLSearchParams(paramsByMode);
            params.set("bookId", bookId);
            return fetch(`/api/transactions?${params.toString()}`);
          }),
        );

        const txPayloads = await Promise.all(txResponses.map((res) => parseJson<{ transactions?: Transaction[] }>(res)));
        const transactions = txPayloads.flatMap((payload) => payload?.transactions ?? []);

        const { income, expense } = sumByType(transactions);
        const monthBalance = income - expense;

        const assetUrl =
          selected.type === "all"
            ? "/api/opening-funds/summary?scope=all"
            : `/api/opening-funds/summary?bookId=${selected.id}`;
        const assetRes = await fetch(assetUrl);
        const assetData = await parseJson<{ assets?: AssetItem[]; total?: number }>(assetRes);
        const openingFundTotal = Number(assetData?.total ?? 0);

        setSummary({
          income,
          expense,
          monthBalance,
          runningBalance: openingFundTotal + monthBalance,
          openingFundTotal,
        });
        setBreakdown(buildBreakdown(transactions));
        setTrend(buildTrend(transactions));
        setRecent(
          transactions
            .sort((a, b) => b.date.localeCompare(a.date))
            .slice(0, 8),
        );
        setAssetBreakdown(assetData?.assets ?? []);
      } catch {
        setSummary({ ...emptySummary });
        setBreakdown([]);
        setTrend([]);
        setRecent([]);
        setAssetBreakdown([]);
      }
    };

    void load();
  }, [books, scopes, scopeId, dateMode, month, rangeStart, rangeEnd]);

  const expenseBreakdown = useMemo(
    () => breakdown.filter((item) => item.type === "expense" && item.amount > 0).slice(0, 8),
    [breakdown],
  );

  const assetRatio = useMemo(
    () => assetBreakdown.filter((item) => item.amount > 0).slice(0, 8),
    [assetBreakdown],
  );

  const totalExpense = useMemo(
    () => expenseBreakdown.reduce((sum, item) => sum + item.amount, 0),
    [expenseBreakdown],
  );
  const totalAsset = useMemo(() => assetRatio.reduce((sum, item) => sum + item.amount, 0), [assetRatio]);

  return (
    <div className="space-y-5">
      <section className="card p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-2">
            {scopes.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setScopeId(item.id)}
                className={`btn ${item.id === scopeId ? "btn-primary" : "btn-muted"}`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <select className="input max-w-36" value={dateMode} onChange={(e) => setDateMode(e.target.value as DateMode)}>
            <option value="all">全部</option>
            <option value="month">按月份</option>
            <option value="range">时间段</option>
          </select>
          {dateMode === "month" && (
            <input type="month" className="input max-w-44" value={month} onChange={(e) => setMonth(e.target.value)} />
          )}
          {dateMode === "range" && (
            <>
              <input type="date" className="input max-w-44" value={rangeStart} onChange={(e) => setRangeStart(e.target.value)} />
              <span className="text-sm text-stone-500">至</span>
              <input type="date" className="input max-w-44" value={rangeEnd} onChange={(e) => setRangeEnd(e.target.value)} />
            </>
          )}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-5">
        <article className="card p-4">
          <p className="text-sm text-stone-500">起始资金</p>
          <p className="mt-1 text-2xl font-semibold text-stone-900">{formatCurrency(summary.openingFundTotal)}</p>
        </article>
        <article className="card p-4">
          <p className="text-sm text-stone-500">收入</p>
          <p className="mt-1 text-2xl font-semibold text-emerald-700">{formatCurrency(summary.income)}</p>
        </article>
        <article className="card p-4">
          <p className="text-sm text-stone-500">支出</p>
          <p className="mt-1 text-2xl font-semibold text-rose-700">{formatCurrency(summary.expense)}</p>
        </article>
        <article className="card p-4">
          <p className="text-sm text-stone-500">净流入</p>
          <p className="mt-1 text-2xl font-semibold text-stone-900">{formatCurrency(summary.monthBalance)}</p>
        </article>
        <article className="card p-4">
          <p className="text-sm text-stone-500">筛选后总资金</p>
          <p className="mt-1 text-2xl font-semibold text-stone-900">{formatCurrency(summary.runningBalance)}</p>
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <article className="card h-[320px] p-4 lg:col-span-2">
          <h2 className="mb-3 text-base font-semibold">收支趋势</h2>
          <ResponsiveContainer width="100%" height="88%">
            <LineChart data={trend}>
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(value) => formatCurrency(Number(value ?? 0))} />
              <Line type="monotone" dataKey="income" stroke="#15803d" strokeWidth={2} />
              <Line type="monotone" dataKey="expense" stroke="#dc2626" strokeWidth={2} />
              <Line type="monotone" dataKey="balance" stroke="#1f2937" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </article>
        <article className="card h-[320px] p-4">
          <h2 className="mb-3 text-base font-semibold">家庭总资产占比</h2>
          <ResponsiveContainer width="100%" height="88%">
            <PieChart>
              <Pie data={assetRatio} dataKey="amount" nameKey="name" outerRadius={95} label>
                {assetRatio.map((item, index) => (
                  <Cell key={item.name} fill={pieColors[index % pieColors.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value, name) => {
                  const amount = Number(value ?? 0);
                  const percent = totalAsset > 0 ? ((amount / totalAsset) * 100).toFixed(1) : "0.0";
                  return [`${formatCurrency(amount)} (${percent}%)`, name];
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="card h-[320px] p-4">
        <h2 className="mb-3 text-base font-semibold">分类占比（支出）</h2>
        <ResponsiveContainer width="100%" height="88%">
          <PieChart>
            <Pie data={expenseBreakdown} dataKey="amount" nameKey="categoryName" outerRadius={95} label>
              {expenseBreakdown.map((item, index) => (
                <Cell key={item.categoryId} fill={pieColors[index % pieColors.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => {
                const amount = Number(value ?? 0);
                const percent = totalExpense > 0 ? ((amount / totalExpense) * 100).toFixed(1) : "0.0";
                return [`${formatCurrency(amount)} (${percent}%)`, name];
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </section>

      <section className="card p-4">
        <h2 className="mb-3 text-base font-semibold">最近流水</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-stone-500">
                <th className="pb-2 pr-3">日期</th>
                <th className="pb-2 pr-3">类型</th>
                <th className="pb-2 pr-3">分类</th>
                <th className="pb-2 pr-3">金额</th>
                <th className="pb-2 pr-3">备注</th>
                <th className="pb-2 pr-3">关联</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((row) => (
                <tr key={row.id} className="border-b border-stone-100">
                  <td className="py-2 pr-3">{row.date.slice(0, 10)}</td>
                  <td className="py-2 pr-3">{row.type === "income" ? "收入" : "支出"}</td>
                  <td className="py-2 pr-3">{row.category.name}</td>
                  <td className="py-2 pr-3">{formatCurrency(row.amount)}</td>
                  <td className="py-2 pr-3">{row.note || "-"}</td>
                  <td className="py-2 pr-3">{row.relationKey || "-"}</td>
                </tr>
              ))}
              {recent.length === 0 && (
                <tr>
                  <td className="py-4 text-stone-500" colSpan={6}>
                    当前筛选条件下暂无记录
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
