"use client";

import { useEffect, useState } from "react";

type Book = { id: string; name: "child" | "family"; displayName: string };
type Category = {
  id: string;
  name: string;
  type: "income" | "expense";
  isDefault: boolean;
  bookId: string | null;
};

export default function CategorySettingsPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [bookId, setBookId] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
  const [name, setName] = useState("");
  const [type, setType] = useState<"income" | "expense">("expense");
  const [scope, setScope] = useState<"global" | "book">("book");

  useEffect(() => {
    const init = async () => {
      const res = await fetch("/api/books");
      const data = await res.json();
      const nextBooks = data.books as Book[];
      setBooks(nextBooks);
      const family = nextBooks.find((book) => book.name === "family");
      setBookId(family?.id || nextBooks[0]?.id || "");
    };
    void init();
  }, []);

  const loadCategories = async (nextBookId: string) => {
    if (!nextBookId) return;
    const res = await fetch(`/api/categories?bookId=${nextBookId}`);
    const data = await res.json();
    setCategories(data.categories ?? []);
  };

  useEffect(() => {
    if (!bookId) return;
    fetch(`/api/categories?bookId=${bookId}`)
      .then((res) => res.json())
      .then((data) => setCategories(data.categories ?? []));
  }, [bookId]);

  const onCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    const res = await fetch("/api/categories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        type,
        bookId: scope === "book" ? bookId : null,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.error || "创建失败");
      return;
    }

    setName("");
    await loadCategories(bookId);
  };

  const onRename = async (category: Category) => {
    const nextName = prompt("输入新的分类名", category.name);
    if (!nextName || nextName === category.name) return;

    await fetch(`/api/categories/${category.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: nextName }),
    });
    await loadCategories(bookId);
  };

  const onDelete = async (category: Category) => {
    if (!confirm(`确认删除分类 ${category.name} ?`)) return;
    const res = await fetch(`/api/categories/${category.id}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json();
      alert(err.error || "删除失败");
      return;
    }
    await loadCategories(bookId);
  };

  return (
    <div className="space-y-5">
      <section className="card p-4">
        <h1 className="mb-3 text-lg font-semibold">分类管理</h1>
        <form onSubmit={onCreate} className="grid gap-3 md:grid-cols-5">
          <select className="input" value={bookId} onChange={(e) => setBookId(e.target.value)}>
            {books.map((book) => (
              <option key={book.id} value={book.id}>
                {book.displayName}
              </option>
            ))}
          </select>
          <select className="input" value={type} onChange={(e) => setType(e.target.value as "income" | "expense")}>
            <option value="expense">支出分类</option>
            <option value="income">收入分类</option>
          </select>
          <select className="input" value={scope} onChange={(e) => setScope(e.target.value as "global" | "book")}>
            <option value="book">当前账本</option>
            <option value="global">全局分类</option>
          </select>
          <input
            className="input"
            placeholder="新分类名称"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <button type="submit" className="btn btn-primary">
            新增分类
          </button>
        </form>
      </section>

      <section className="card p-4">
        <h2 className="mb-3 text-base font-semibold">当前分类</h2>
        <div className="grid gap-2">
          {categories.map((category) => (
            <article
              key={category.id}
              className="flex items-center justify-between rounded-lg border border-stone-200 bg-white p-3"
            >
              <div>
                <p className="font-medium">{category.name}</p>
                <p className="text-xs text-stone-500">
                  {category.type === "income" ? "收入" : "支出"} · {category.bookId ? "账本私有" : "全局"}
                  {category.isDefault ? " · 默认" : ""}
                </p>
              </div>
              <div className="flex gap-2">
                <button type="button" className="btn btn-muted" onClick={() => void onRename(category)}>
                  重命名
                </button>
                {!category.isDefault && (
                  <button type="button" className="btn btn-danger" onClick={() => void onDelete(category)}>
                    删除
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
