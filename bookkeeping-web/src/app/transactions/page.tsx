"use client";

import { useEffect, useMemo, useState } from "react";
import { currentMonth, formatCurrency, todayString } from "@/lib/ui";

type Book = { id: string; name: "child" | "family"; displayName: string };
type Category = { id: string; name: string; type: "income" | "expense"; bookId: string | null };
type Transaction = {
  id: string;
  date: string;
  type: "income" | "expense";
  amount: number;
  note?: string | null;
  relationKey?: string | null;
  categoryId: string;
  category: { name: string };
};

export default function TransactionsPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [bookId, setBookId] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);

  const [date, setDate] = useState(todayString());
  const [type, setType] = useState<"income" | "expense">("expense");
  const [categoryId, setCategoryId] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [relationKey, setRelationKey] = useState("");

  const [month, setMonth] = useState(currentMonth());
  const [q, setQ] = useState("");
  const [relationSearch, setRelationSearch] = useState("");

  const filteredCategories = useMemo(() => categories.filter((c) => c.type === type), [categories, type]);
  const selectedCategoryId = useMemo(() => {
    if (filteredCategories.some((item) => item.id === categoryId)) return categoryId;
    return filteredCategories[0]?.id ?? "";
  }, [categoryId, filteredCategories]);

  useEffect(() => {
    const loadBooks = async () => {
      const res = await fetch("/api/books");
      const data = await res.json();
      const nextBooks = data.books as Book[];
      setBooks(nextBooks);
      const family = nextBooks.find((book) => book.name === "family");
      setBookId((prev) => prev || family?.id || nextBooks[0]?.id || "");
    };
    void loadBooks();
  }, []);

  useEffect(() => {
    if (!bookId) return;
    const loadCategories = async () => {
      const res = await fetch(`/api/categories?bookId=${bookId}`);
      const data = await res.json();
      setCategories(data.categories ?? []);
    };
    void loadCategories();
  }, [bookId]);

  const loadTransactions = async () => {
    if (!bookId) return;
    const params = new URLSearchParams({ bookId, month, limit: "200" });
    if (q) params.set("q", q);
    if (relationSearch) params.set("relationKey", relationSearch);
    const res = await fetch(`/api/transactions?${params.toString()}`);
    const data = await res.json();
    setTransactions(data.transactions ?? []);
  };

  useEffect(() => {
    if (!bookId) return;
    const params = new URLSearchParams({ bookId, month, limit: "200" });
    fetch(`/api/transactions?${params.toString()}`)
      .then((res) => res.json())
      .then((data) => setTransactions(data.transactions ?? []));
  }, [bookId, month]);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedCategoryId) {
      alert("请先配置分类");
      return;
    }
    const res = await fetch("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        bookId,
        date,
        type,
        categoryId: selectedCategoryId,
        amount: Number(amount),
        note,
        relationKey,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.error || "保存失败");
      return;
    }

    setAmount("");
    setNote("");
    setRelationKey("");
    await loadTransactions();
  };

  const onDelete = async (id: string) => {
    if (!confirm("确认删除这条流水？")) return;
    await fetch(`/api/transactions/${id}`, { method: "DELETE" });
    await loadTransactions();
  };

  const onEdit = async (tx: Transaction) => {
    const newAmount = prompt("修改金额", String(tx.amount));
    if (!newAmount) return;
    const newNote = prompt("修改备注", tx.note || "") ?? tx.note;
    const newRelation = prompt("修改关联ID", tx.relationKey || "") ?? tx.relationKey;

    await fetch(`/api/transactions/${tx.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount: Number(newAmount), note: newNote, relationKey: newRelation }),
    });
    await loadTransactions();
  };

  return (
    <div className="space-y-5">
      <section className="card p-4">
        <h1 className="mb-3 text-lg font-semibold">快速记一笔</h1>
        <form onSubmit={onSubmit} className="grid gap-3 md:grid-cols-6">
          <select className="input" value={bookId} onChange={(e) => setBookId(e.target.value)}>
            {books.map((book) => (
              <option key={book.id} value={book.id}>
                {book.displayName}
              </option>
            ))}
          </select>
          <input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
          <select className="input" value={type} onChange={(e) => setType(e.target.value as "income" | "expense")}>
            <option value="expense">支出</option>
            <option value="income">收入</option>
          </select>
          <select className="input" value={selectedCategoryId} onChange={(e) => setCategoryId(e.target.value)}>
            {filteredCategories.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          <input
            type="number"
            min="0"
            step="0.01"
            placeholder="金额"
            className="input"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
          />
          <input
            className="input"
            placeholder="关联ID（可选）"
            value={relationKey}
            onChange={(e) => setRelationKey(e.target.value)}
          />
          <input
            className="input md:col-span-5"
            placeholder="备注（支持关键字搜索）"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button type="submit" className="btn btn-primary">
            保存
          </button>
        </form>
      </section>

      <section className="card p-4">
        <div className="mb-3 grid gap-3 md:grid-cols-5">
          <input type="month" className="input" value={month} onChange={(e) => setMonth(e.target.value)} />
          <input className="input" placeholder="关键字搜索" value={q} onChange={(e) => setQ(e.target.value)} />
          <input
            className="input"
            placeholder="关联ID搜索"
            value={relationSearch}
            onChange={(e) => setRelationSearch(e.target.value)}
          />
          <button type="button" className="btn btn-muted" onClick={() => void loadTransactions()}>
            查询
          </button>
          <div className="self-center text-right text-sm text-stone-500">共 {transactions.length} 条</div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-stone-500">
                <th className="pb-2 pr-2">日期</th>
                <th className="pb-2 pr-2">类型</th>
                <th className="pb-2 pr-2">分类</th>
                <th className="pb-2 pr-2">金额</th>
                <th className="pb-2 pr-2">备注</th>
                <th className="pb-2 pr-2">关联</th>
                <th className="pb-2 pr-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id} className="border-b border-stone-100">
                  <td className="py-2 pr-2">{tx.date.slice(0, 10)}</td>
                  <td className="py-2 pr-2">{tx.type === "income" ? "收入" : "支出"}</td>
                  <td className="py-2 pr-2">{tx.category.name}</td>
                  <td className="py-2 pr-2">{formatCurrency(tx.amount)}</td>
                  <td className="py-2 pr-2">{tx.note || "-"}</td>
                  <td className="py-2 pr-2">{tx.relationKey || "-"}</td>
                  <td className="py-2 pr-2">
                    <div className="flex gap-2">
                      <button type="button" className="btn btn-muted" onClick={() => void onEdit(tx)}>
                        编辑
                      </button>
                      <button type="button" className="btn btn-danger" onClick={() => void onDelete(tx.id)}>
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
