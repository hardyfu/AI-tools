"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "仪表盘" },
  { href: "/transactions", label: "流水" },
  { href: "/salary", label: "工资分配" },
  { href: "/settings/opening-funds", label: "起始资金" },
  { href: "/settings/categories", label: "分类设置" },
];

export function TopNav() {
  const pathname = usePathname();

  const onExit = async () => {
    try {
      await fetch("/api/exit", { method: "POST" });
    } finally {
      window.location.href = "about:blank";
      window.close();
    }
  };

  return (
    <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
        <span className="text-lg font-semibold tracking-tight text-stone-800">极简记账</span>
        <div className="flex items-center gap-3">
          <nav className="flex items-center gap-2">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-md px-3 py-1.5 text-sm transition ${
                  active
                    ? "bg-stone-900 text-white"
                    : "text-stone-600 hover:bg-stone-100 hover:text-stone-900"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
          </nav>
          <button type="button" className="btn btn-danger" onClick={() => void onExit()}>
            退出
          </button>
        </div>
      </div>
    </header>
  );
}
