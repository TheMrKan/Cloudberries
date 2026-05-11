import { useState, useEffect, useRef } from "react";
import { Cloud, Send, Plus, Sun, Moon, Search, ExternalLink, Maximize2, Minimize2, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./components/ui/button";
import { Textarea } from "./components/ui/textarea";
import { Card } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Skeleton } from "./components/ui/skeleton";

// ---------- Types ----------
interface ServiceItem {
  id: string;
  name: string;
  provider: string;
  tags: string[];
  description: string;
  url: string;
  fz152: boolean;
  platform?: string;
  region: string;
}

interface ServiceResult extends ServiceItem {
  rationale: string;
  priceScore: number;
  taskMatchScore: number;
  criteriaMatchScore: number;
  pricing_elements: Array<{ description: string; uom: string; price: number }>;
}

type Phase = "catalog" | "chat" | "results";

interface HistoryEntry {
  query: string;
  results: ServiceResult[];
  messages: { role: "user" | "assistant"; text: string }[];
}

// ---------- Provider assets ----------
const PROVIDER_LOGOS: Record<string, string> = {
  "Т1 Облако": "https://t1-cloud.ru/favicon.ico",
  "Cloud.ru": "https://www.google.com/s2/favicons?domain=cloud.ru&sz=64",
  "Selectel": "https://selectel.ru/favicon.ico",
  "VK Cloud": "https://www.google.com/s2/favicons?domain=cloud.vk.com&sz=64",
  "Yandex Cloud": "https://yandex.cloud/favicon.ico",
};

function ProviderIcon({ provider, size = "md" }: { provider: string; size?: "sm" | "md" }) {
  const url = PROVIDER_LOGOS[provider];
  const dim = size === "sm" ? "w-6 h-6" : "w-9 h-9";
  if (!url) return null;
  return (
    <div className={`${dim} rounded-lg bg-white dark:bg-gray-800 flex items-center justify-center shadow-sm ring-1 ring-gray-200 dark:ring-gray-700 shrink-0 overflow-hidden`}>
      <img src={url} alt={provider} className="w-full h-full object-contain p-0.5" />
    </div>
  );
}

// ---------- Mock data ----------
const ALL_SERVICES: ServiceItem[] = [
  { id: "1", name: "Compute (Cloud Engine)", provider: "Т1 Облако", tags: ["VPS", "OpenStack", "152-ФЗ"], description: "Облачные ресурсы для создания масштабируемой вычислительной инфраструктуры, администрирования и сопровождения сервисов на платформе OpenStack.", url: "https://t1-cloud.ru/services/compute", fz152: true, platform: "OpenStack", region: "Москва" },
  { id: "2", name: "Объектное хранилище S3", provider: "Т1 Облако", tags: ["S3", "152-ФЗ", "OpenStack"], description: "S3-совместимое объектное хранилище с мультизональным размещением для файлов, статики, бэкапов и архивов.", url: "https://t1-cloud.ru/services/s3", fz152: true, platform: "OpenStack", region: "Москва" },
  { id: "3", name: "Managed Kubernetes", provider: "Т1 Облако", tags: ["K8s", "152-ФЗ", "OpenStack"], description: "Управляемый кластер Kubernetes с автоскейлингом и интеграцией в OpenStack.", url: "https://t1-cloud.ru/services/kubernetes", fz152: true, platform: "OpenStack", region: "Москва" },
  { id: "4", name: "Managed PostgreSQL", provider: "Т1 Облако", tags: ["БД", "PostgreSQL", "152-ФЗ"], description: "DBaaS на базе PostgreSQL с автоматическим бэкапом, репликацией и мониторингом.", url: "https://t1-cloud.ru/services/postgresql", fz152: true, platform: "OpenStack", region: "Москва" },
  { id: "5", name: "Evolution Object Storage", provider: "Cloud.ru", tags: ["S3", "152-ФЗ", "Multi-AZ"], description: "Масштабируемое S3-хранилище с автоматическим масштабированием, версионированием и AWS S3 API.", url: "https://cloud.ru/services/object-storage", fz152: true, region: "Москва" },
  { id: "6", name: "Cloud Servers", provider: "VK Cloud", tags: ["VPS", "VMware"], description: "Виртуальные серверы с быстрой сетью и гибкими конфигурациями.", url: "https://cloud.vk.com/services/servers", fz152: false, platform: "VMware", region: "Москва, Санкт-Петербург" },
  { id: "7", name: "S3-хранилище", provider: "Selectel", tags: ["S3", "холодное хранение"], description: "Объектное хранилище с горячим и холодным классами для бэкапов и архивов.", url: "https://selectel.ru/services/storage/s3/", fz152: false, region: "Москва, Санкт-Петербург" },
  { id: "8", name: "Compute Cloud", provider: "Yandex Cloud", tags: ["VPS", "посекундная оплата"], description: "Виртуальные машины с посекундной оплатой и интеграцией с сервисами Yandex Cloud.", url: "https://yandex.cloud/ru/services/compute", fz152: false, region: "Москва, Владимирская обл." },
  { id: "9", name: "Managed Databases", provider: "Yandex Cloud", tags: ["БД", "PostgreSQL", "MySQL"], description: "Управляемые БД PostgreSQL, MySQL, ClickHouse с авто-бэкапом и масштабированием.", url: "https://yandex.cloud/ru/services/managed-postgresql", fz152: false, region: "Москва, Владимирская обл." },
  { id: "10", name: "Cloud Storage", provider: "VK Cloud", tags: ["S3", "Hotbox", "Icebox"], description: "Объектное хранилище с горячим и холодным классами.", url: "https://cloud.vk.com/services/storage", fz152: false, region: "Москва, Санкт-Петербург" },
  { id: "11", name: "VPS (Virtual Private Server)", provider: "Selectel", tags: ["VPS", "VMware"], description: "Виртуальные серверы с выделенными ресурсами и быстрым масштабированием.", url: "https://selectel.ru/services/vps/", fz152: false, platform: "VMware", region: "Москва, Санкт-Петербург" },
  { id: "12", name: "Cloud Servers", provider: "Cloud.ru", tags: ["VPS", "OpenStack", "152-ФЗ"], description: "Виртуальные машины на OpenStack с высокой доступностью и 152-ФЗ.", url: "https://cloud.ru/services/servers", fz152: true, platform: "OpenStack", region: "Москва" },
];

const MOCK_RESULTS: ServiceResult[] = [
  { id: "r1", name: "Объектное хранилище S3", provider: "Т1 Облако", tags: ["S3", "152-ФЗ", "OpenStack"], description: "S3-хранилище с мультизональным размещением и интеграцией с OpenStack.", url: "https://t1-cloud.ru/services/s3", fz152: true, platform: "OpenStack", region: "Москва", rationale: "Наиболее выгодное предложение в заданном бюджете (2000 руб/мес). Полное соответствие 152-ФЗ, мультизональный S3 повышает надёжность.", priceScore: 9, taskMatchScore: 9, criteriaMatchScore: 8, pricing_elements: [
    { description: "Объектное хранилище (S3), хранение данных", uom: "ГБ*мин", price: 0.00003819 },
    { description: "Объектное хранилище (S3), скачивание данных", uom: "ГБ", price: 0.25 },
    { description: "Объектное хранилище (S3), запросы Put/Post", uom: "1000 шт", price: 0.24 },
    { description: "Объектное хранилище (S3), запросы Get/Head", uom: "10 000 шт", price: 0.24 },
    { description: "Объектное хранилище (мультизональное S3), хранение данных", uom: "ГБ*мин", price: 0.00006906 },
    { description: "Объектное хранилище (мультизональное S3), скачивание данных", uom: "ГБ", price: 0.50 },
    { description: "Объектное хранилище (мультизональное S3), запросы Put/Post", uom: "1000 шт", price: 0.24 },
    { description: "Объектное хранилище (мультизональное S3), запросы Get/Head", uom: "10 000 шт", price: 0.24 },
  ] },
  { id: "r2", name: "Evolution Object Storage", provider: "Cloud.ru", tags: ["S3", "152-ФЗ", "Multi-AZ"], description: "S3-хранилище от Cloud.ru с версионированием и совместимостью S3 API.", url: "https://cloud.ru/services/object-storage", fz152: true, region: "Москва", rationale: "Отличная альтернатива с мощным функционалом. Дороже Т1, но предоставляет больше гибкости и глобальную CDN.", priceScore: 8, taskMatchScore: 10, criteriaMatchScore: 9, pricing_elements: [
    { description: "Evolution Object Storage, хранение", uom: "ГБ", price: 2.5 },
    { description: "Evolution Object Storage, запросы Put/Post", uom: "1000 шт", price: 0.30 },
    { description: "Evolution Object Storage, запросы Get/Head", uom: "10 000 шт", price: 0.20 },
    { description: "Evolution Object Storage, исходящий трафик", uom: "ГБ", price: 1.0 },
  ] },
  { id: "r3", name: "Cloud Storage", provider: "VK Cloud", tags: ["S3", "Hotbox", "Icebox"], description: "Объектное хранилище VK Cloud с горячим и холодным классами.", url: "https://cloud.vk.com/services/storage", fz152: false, region: "Москва, Санкт-Петербург", rationale: "Самое бюджетное решение при больших объёмах. Без официального статуса 152-ФЗ.", priceScore: 10, taskMatchScore: 7, criteriaMatchScore: 6, pricing_elements: [
    { description: "Cloud Storage (Hotbox), хранение", uom: "ГБ", price: 1.8 },
    { description: "Cloud Storage (Icebox), хранение", uom: "ГБ", price: 0.9 },
    { description: "Cloud Storage, запросы Put/Post", uom: "1000 шт", price: 0.20 },
    { description: "Cloud Storage, запросы Get/Head", uom: "10 000 шт", price: 0.15 },
    { description: "Cloud Storage, исходящий трафик", uom: "ГБ", price: 0.80 },
  ] },
];

const MOCK_RESULTS_2: ServiceResult[] = [
  { id: "r4", name: "Managed Kubernetes", provider: "Т1 Облако", tags: ["K8s", "152-ФЗ", "OpenStack"], description: "Управляемый кластер Kubernetes с автоскейлингом и интеграцией в OpenStack.", url: "https://t1-cloud.ru/services/kubernetes", fz152: true, platform: "OpenStack", region: "Москва", rationale: "Лучшее решение для контейнеризации в Москве. Полное соответствие 152-ФЗ, интеграция с OpenStack.", priceScore: 8, taskMatchScore: 9, criteriaMatchScore: 8, pricing_elements: [
    { description: "Kubernetes, мастер-узел", uom: "час", price: 12 },
    { description: "Kubernetes, рабочий узел", uom: "час", price: 3.5 },
    { description: "Kubernetes, нагрузочный балансировщик", uom: "час", price: 1.2 },
    { description: "Kubernetes, хранение данных", uom: "ГБ", price: 2 },
  ] },
  { id: "r5", name: "Managed PostgreSQL", provider: "Т1 Облако", tags: ["БД", "PostgreSQL", "152-ФЗ"], description: "DBaaS на базе PostgreSQL с автоматическим бэкапом, репликацией и мониторингом.", url: "https://t1-cloud.ru/services/postgresql", fz152: true, platform: "OpenStack", region: "Москва", rationale: "Надёжная управляемая БД с полным соответствием 152-ФЗ и автоматическим резервным копированием.", priceScore: 7, taskMatchScore: 8, criteriaMatchScore: 9, pricing_elements: [
    { description: "PostgreSQL, 1 vCPU + 2 ГБ RAM", uom: "час", price: 2.5 },
    { description: "PostgreSQL, хранилище SSD", uom: "ГБ", price: 5 },
    { description: "PostgreSQL, резервные копии", uom: "ГБ", price: 1 },
  ] },
  { id: "r6", name: "Cloud Servers", provider: "Cloud.ru", tags: ["VPS", "OpenStack", "152-ФЗ"], description: "Виртуальные машины на OpenStack с высокой доступностью и 152-ФЗ.", url: "https://cloud.ru/services/servers", fz152: true, platform: "OpenStack", region: "Москва", rationale: "Гибкие виртуальные серверы с посекундной оплатой и соответствием 152-ФЗ.", priceScore: 8, taskMatchScore: 7, criteriaMatchScore: 8, pricing_elements: [
    { description: "Cloud Servers, 1 vCPU + 1 ГБ RAM", uom: "час", price: 1.5 },
    { description: "Cloud Servers, 2 vCPU + 4 ГБ RAM", uom: "час", price: 3.8 },
    { description: "Cloud Servers, SSD диск", uom: "ГБ", price: 4 },
    { description: "Cloud Servers, бэкапы", uom: "ГБ", price: 0.5 },
  ] },
];

const MOCK_RESULTS_3: ServiceResult[] = [
  { id: "r7", name: "Compute (Cloud Engine)", provider: "Т1 Облако", tags: ["VPS", "OpenStack", "152-ФЗ"], description: "Облачные ресурсы для создания масштабируемой вычислительной инфраструктуры на платформе OpenStack.", url: "https://t1-cloud.ru/services/compute", fz152: true, platform: "OpenStack", region: "Москва", rationale: "Мощная вычислительная платформа с широкими возможностями кастомизации и полным комплаенсом.", priceScore: 7, taskMatchScore: 8, criteriaMatchScore: 7, pricing_elements: [
    { description: "Compute, 1 vCPU + 2 ГБ RAM", uom: "час", price: 1.8 },
    { description: "Compute, 4 vCPU + 8 ГБ RAM", uom: "час", price: 5.2 },
    { description: "Compute, SSD диск", uom: "ГБ", price: 3 },
  ] },
  { id: "r8", name: "VPS (Virtual Private Server)", provider: "Selectel", tags: ["VPS", "VMware"], description: "Виртуальные серверы с выделенными ресурсами и быстрым масштабированием.", url: "https://selectel.ru/services/vps/", fz152: false, platform: "VMware", region: "Москва, Санкт-Петербург", rationale: "Доступные виртуальные серверы с быстрой сетью и гибкой конфигурацией без 152-ФЗ.", priceScore: 9, taskMatchScore: 6, criteriaMatchScore: 5, pricing_elements: [
    { description: "VPS, 1 vCPU + 1 ГБ RAM", uom: "месяц", price: 350 },
    { description: "VPS, 2 vCPU + 4 ГБ RAM", uom: "месяц", price: 750 },
    { description: "VPS, SSD диск", uom: "ГБ", price: 2.5 },
  ] },
  { id: "r9", name: "Managed Databases", provider: "Yandex Cloud", tags: ["БД", "PostgreSQL", "MySQL"], description: "Управляемые БД PostgreSQL, MySQL, ClickHouse с авто-бэкапом и масштабированием.", url: "https://yandex.cloud/ru/services/managed-postgresql", fz152: false, region: "Москва, Владимирская обл.", rationale: "Широкий выбор СУБД с автоматическим масштабированием. Без 152-ФЗ, но с высокой отказоустойчивостью.", priceScore: 8, taskMatchScore: 8, criteriaMatchScore: 7, pricing_elements: [
    { description: "PostgreSQL, 1 vCPU + 2 ГБ RAM", uom: "час", price: 2.2 },
    { description: "PostgreSQL, SSD диск", uom: "ГБ", price: 3.5 },
    { description: "PostgreSQL, бэкапы", uom: "ГБ", price: 0.8 },
  ] },
];

const MOCK_SETS = [MOCK_RESULTS, MOCK_RESULTS_2, MOCK_RESULTS_3];

// ---------- Score bar ----------
function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted-foreground font-medium">{label}</span>
        <span className="font-bold tabular-nums">{value}/10</span>
      </div>
      <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-[#1DAFF7] to-[#008ACD] rounded-full transition-all duration-700" style={{ width: `${(value / 10) * 100}%` }} />
      </div>
    </div>
  );
}

function MetricRow({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex justify-between items-center gap-2">
      <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className={`font-semibold text-right text-xs leading-tight ${valueClass || ""}`}>{value}</span>
    </div>
  );
}

// ========== CATALOG CARD ==========
function CatalogCard({ service }: { service: ServiceItem }) {
  return (
    <Card className="overflow-hidden transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col flex-1">
      <div className="p-3 sm:p-5 flex flex-col flex-1 gap-2">
        <h3 className="text-base font-bold leading-tight line-clamp-2">{service.name}</h3>
        <div className="flex items-center gap-2">
          <ProviderIcon provider={service.provider} size="sm" />
          <span className="text-xs font-medium text-muted-foreground">{service.provider}</span>
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground line-clamp-3">{service.description}</p>
        <a href={service.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-medium text-[#1DAFF7] hover:text-[#008ACD] transition-colors">
          Подробнее <ExternalLink className="w-3 h-3" />
        </a>
        <div className="bg-muted/50 rounded-lg p-3 space-y-1.5 border">
          <MetricRow label="152-ФЗ" value={service.fz152 ? "Да" : "Нет"} valueClass={service.fz152 ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"} />
          {service.tags.includes("VPS") && service.platform && <MetricRow label="Платформа" value={service.platform} />}
          <MetricRow label="Регионы" value={service.region} />
        </div>
      </div>
    </Card>
  );
}

// ========== RESULT CARD ==========
const RANK_STYLES: Record<number, { border: string; rankColor: string }> = {
  1: { border: "ring-2 ring-[#FFD700]", rankColor: "text-[#FFD700]" },
  2: { border: "ring-2 ring-[#C0C0C0]", rankColor: "text-[#C0C0C0]" },
  3: { border: "ring-2 ring-[#CD7F32]", rankColor: "text-[#CD7F32]" },
};

function ResultCardFull({ result, rank }: { result: ServiceResult; rank: number }) {
  const style = RANK_STYLES[rank] || RANK_STYLES[3];
  return (
    <Card className={`overflow-hidden flex flex-col flex-1 ${style.border}`}>
      <div className="p-3 sm:p-5 flex flex-col gap-3 flex-1">
        <div className="flex items-center gap-2">
          <span className={`text-lg font-black tracking-tight ${style.rankColor}`}>#{rank}</span>
          <ProviderIcon provider={result.provider} size="sm" />
          <span className="text-xs font-medium text-muted-foreground">{result.provider}</span>
        </div>
        <h3 className="text-sm font-bold leading-tight">{result.name}</h3>
        <p className="text-xs leading-relaxed text-muted-foreground line-clamp-3">{result.description}</p>
        <a href={result.url} target="_blank" rel="noreferrer" className="text-xs font-medium text-[#1DAFF7] hover:text-[#008ACD] inline-flex items-center gap-1 transition-colors">
          Подробнее <ExternalLink className="w-3 h-3" />
        </a>
        <div className="bg-muted/50 rounded-lg p-3 space-y-1.5 border">
          <MetricRow label="152-ФЗ" value={result.fz152 ? "Да" : "Нет"} valueClass={result.fz152 ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"} />
          {result.platform && <MetricRow label="Платформа" value={result.platform} />}
          <MetricRow label="Регионы" value={result.region} />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {result.tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="text-[10px] px-2 py-0.5 bg-gradient-to-r from-sky-50 to-blue-50 dark:from-sky-900/30 dark:to-blue-900/30 text-[#1DAFF7] border-sky-100/50 dark:border-sky-700/30">
              {tag}
            </Badge>
          ))}
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground">{result.rationale}</p>
        <div className="bg-muted/50 rounded-lg p-3 space-y-2 border">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Скоринг</div>
          <ScoreBar label="Цена" value={result.priceScore} />
          <ScoreBar label="Соответствие задаче" value={result.taskMatchScore} />
          <ScoreBar label="Соответствие критериям" value={result.criteriaMatchScore} />
        </div>
        {result.pricing_elements && result.pricing_elements.length > 0 && (
          <div className="bg-muted/50 rounded-lg p-3 border">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">Тарификация</div>
            <table className="w-full text-[11px]">
              <tbody>
                {result.pricing_elements.slice(0, 5).map((el, i) => (
                  <tr key={i} className="border-t border-border/40 first:border-t-0">
                    <td className="py-1 pr-2 text-foreground">{el.description}</td>
                    <td className="py-1 pr-2 text-muted-foreground whitespace-nowrap text-center">{el.uom}</td>
                    <td className="py-1 text-center whitespace-nowrap font-medium tabular-nums">{el.price} ₽</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex-1" />
      </div>
    </Card>
  );
}

// ========== HISTORY OVERLAY ==========
function HistoryOverlay({ messages, onExpand }: { messages: { role: string; text: string }[]; onExpand?: () => void }) {
  const overlayChatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (overlayChatRef.current) {
      overlayChatRef.current.scrollTop = overlayChatRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="absolute bottom-full left-0 right-0 mb-2 bg-card rounded-2xl shadow-xl ring-1 ring-border overflow-hidden">
      <div className="flex items-center justify-between px-4 pt-3 pb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">История чата</span>
        {onExpand && (
          <button onClick={onExpand} className="text-muted-foreground hover:text-foreground transition-colors">
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
      <div ref={overlayChatRef} className="px-3 pb-2 max-h-72 overflow-y-auto space-y-1.5">
        {messages.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">История пуста</p>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`px-3 py-2 text-xs leading-relaxed max-w-[85%] ${
                msg.role === "user"
                  ? "bg-gradient-to-br from-[#1DAFF7] to-[#008ACD] text-white rounded-2xl rounded-br-md"
                  : "bg-muted text-foreground rounded-2xl rounded-bl-md"
              }`}>
                {msg.text}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ========== MAIN APP ==========
export default function App() {
  const [phase, setPhase] = useState<Phase>("catalog");
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [resultsHistory, setResultsHistory] = useState<HistoryEntry[]>([]);
  const [catalogServices, setCatalogServices] = useState<ServiceItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem("theme");
    if (stored) return stored === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const [awaitingClarification, setAwaitingClarification] = useState(false);
  const [selectedResultIdx, setSelectedResultIdx] = useState(0);
  const [showSearchHistory, setShowSearchHistory] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isNewSearch, setIsNewSearch] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);
  const loadingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [splitRatio, setSplitRatio] = useState(0.6);
  const isDragging = useRef(false);
  const splitContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => { pickCatalog(); }, []);

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => { if (loadingTimeout.current) clearTimeout(loadingTimeout.current); };
  }, []);

  function pickCatalog() {
    setCatalogServices([...ALL_SERVICES].sort(() => 0.5 - Math.random()).slice(0, 9));
  }

  function goToCatalog() {
    if (loadingTimeout.current) clearTimeout(loadingTimeout.current);
    setPhase("catalog");
    setMessages([]);
    setResultsHistory([]);
    setSelectedResultIdx(0);
    setIsLoading(false);
    setAwaitingClarification(false);
    setShowSearchHistory(true);
    pickCatalog();
  }

  function addResults(query: string, newResults: ServiceResult[], msgs: { role: "user" | "assistant"; text: string }[]) {
    setResultsHistory((prev) => [{ query, results: newResults, messages: msgs }, ...prev]);
    setSelectedResultIdx(0);
  }

  function updateCurrentEntry(results: ServiceResult[], msgs: { role: "user" | "assistant"; text: string }[]) {
    setResultsHistory((prev) => {
      const updated = [...prev];
      if (updated[selectedResultIdx]) {
        updated[selectedResultIdx] = { ...updated[selectedResultIdx], results, messages: msgs };
      }
      return updated;
    });
  }

  function handleCatalogSearch() {
    if (!input.trim() || isLoading) return;
    const text = input;
    setInput("");
    setMessages([{ role: "user", text }]);
    setIsNewSearch(true);
    setIsLoading(true);
    setPhase("chat");
    loadingTimeout.current = setTimeout(() => {
      loadingTimeout.current = null;
      const newMsg = { role: "assistant" as const, text: "Вот что удалось подобрать по вашему запросу:" };
      setMessages((prev) => [...prev, newMsg]);
      setTimeout(() => addResults(text, MOCK_RESULTS, [...messages, { role: "user" as const, text }, newMsg]), 0);
      setIsLoading(false);
      setIsNewSearch(false);
      setAwaitingClarification(false);
      setPhase("results");
    }, 1800);
  }

  function handleSend() {
    if (!input.trim() || isLoading) return;
    const text = input;
    setInput("");
    const userMsg = { role: "user" as const, text };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    if (phase === "chat" && isNewSearch) {
      loadingTimeout.current = setTimeout(() => {
        loadingTimeout.current = null;
        const assistMsg = { role: "assistant" as const, text: "Вот что удалось подобрать по вашему запросу:" };
        setMessages((prev) => [...prev, assistMsg]);
        setTimeout(() => addResults(text, MOCK_RESULTS, [...messages, userMsg, assistMsg]), 0);
        setIsLoading(false);
        setIsNewSearch(false);
        setAwaitingClarification(false);
        setPhase("results");
      }, 1800);
    } else {
      // Results phase or expanded chat — refine current entry in place
      if (awaitingClarification) {
        loadingTimeout.current = setTimeout(() => {
          loadingTimeout.current = null;
          const assistMsg = { role: "assistant" as const, text: "Вот результаты с учётом ваших уточнений:" };
          setMessages((prev) => [...prev, assistMsg]);
          const setIndex = resultsHistory.length % MOCK_SETS.length;
          const allMsgs = [...messages, userMsg, assistMsg];
          updateCurrentEntry(MOCK_SETS[setIndex], allMsgs);
          setIsLoading(false);
          setAwaitingClarification(false);
          if (phase === "chat") setPhase("results");
        }, 1800);
      } else if (text.length < 20) {
        loadingTimeout.current = setTimeout(() => {
          loadingTimeout.current = null;
          const assistMsg = {
            role: "assistant" as const,
            text: "Уточните, пожалуйста, какой бюджет вы рассматриваете и требуются ли вам соответствие 152-ФЗ?"
          };
          setMessages((prev) => [...prev, assistMsg]);
          const allMsgs = [...messages, userMsg, assistMsg];
          updateCurrentEntry(resultsHistory[selectedResultIdx]?.results || [], allMsgs);
          setIsLoading(false);
          setAwaitingClarification(true);
          if (phase === "chat") setPhase("results");
        }, 1000);
      } else {
        loadingTimeout.current = setTimeout(() => {
          loadingTimeout.current = null;
          const assistMsg = { role: "assistant" as const, text: "Вот обновлённые результаты с учётом ваших уточнений:" };
          setMessages((prev) => [...prev, assistMsg]);
          const setIndex = resultsHistory.length % MOCK_SETS.length;
          const allMsgs = [...messages, userMsg, assistMsg];
          updateCurrentEntry(MOCK_SETS[setIndex], allMsgs);
          setIsLoading(false);
          if (phase === "chat") setPhase("results");
        }, 1800);
      }
    }
  }

  function handleNewSearch() {
    if (loadingTimeout.current) clearTimeout(loadingTimeout.current);
    setMessages([]);
    setIsLoading(false);
    setAwaitingClarification(false);
    setIsNewSearch(true);
    setPhase("chat");
  }

  function showFullChat() {
    setIsNewSearch(false);
    setPhase("chat");
  }

  function goToResults() {
    setPhase("results");
  }

  function ThemeToggle() {
    return (
      <button
        onClick={() => setDark(!dark)}
        className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center text-muted-foreground bg-secondary hover:bg-accent transition-colors shrink-0"
        title={dark ? "Светлая тема" : "Тёмная тема"}
      >
        {dark ? <Sun className="w-4 h-4 sm:w-5 sm:h-5" /> : <Moon className="w-4 h-4 sm:w-5 sm:h-5" />}
      </button>
    );
  }

  function Logo() {
    return (
      <button onClick={goToCatalog} className="flex items-center gap-2 shrink-0 hover:opacity-80 transition-opacity">
        <Cloud className="w-7 h-7 text-[#1DAFF7]" />
        <div className="flex flex-col items-start">
          <span className="text-sm font-bold tracking-tight leading-tight">Cloudberries</span>
          <span className="text-[10px] text-muted-foreground leading-tight hidden sm:block">Маркетплейс облачных находок</span>
        </div>
      </button>
    );
  }

  function RightButtons({ showNewChat }: { showNewChat: boolean }) {
    return (
      <div className="flex items-center gap-1 sm:gap-2 shrink-0">
        {showNewChat && (
          <Button size="sm" onClick={handleNewSearch} className="h-8 sm:h-9">
            <Plus className="w-4 h-4" /> <span className="hidden sm:inline">Подбор сервиса</span>
          </Button>
        )}
        <ThemeToggle />
      </div>
    );
  }

  function MobileHeader({ title, onToggleSidebar }: { title: string; onToggleSidebar?: () => void }) {
    if (onToggleSidebar) {
      return (
        <div className="flex sm:hidden flex-col border-b bg-card shrink-0" style={{ paddingTop: "env(safe-area-inset-top, 8px)" }}>
          <div className="flex items-center justify-between px-4 py-1.5">
            <button onClick={goToCatalog}>
              <Cloud className="w-6 h-6 text-[#1DAFF7]" />
            </button>
            <div className="flex items-center gap-1">
              <button onClick={handleNewSearch} className="w-8 h-8 rounded-xl flex items-center justify-center text-muted-foreground bg-secondary hover:bg-accent transition-colors" title="Подбор сервиса">
                <Plus className="w-4 h-4" />
              </button>
              <ThemeToggle />
            </div>
          </div>
          <div className="flex items-center gap-2 px-4 pb-2">
            <button onClick={onToggleSidebar} className="text-muted-foreground hover:text-foreground transition-colors">
              <ChevronRight className="w-4 h-4" />
            </button>
            <span className="text-sm font-semibold">{title}</span>
          </div>
        </div>
      );
    }
    return (
      <div className="flex sm:hidden items-center justify-between px-4 py-2 border-b bg-card shrink-0" style={{ paddingTop: "env(safe-area-inset-top, 8px)" }}>
        <div className="flex items-center gap-2">
          <button onClick={goToCatalog}>
            <Cloud className="w-6 h-6 text-[#1DAFF7]" />
          </button>
          <span className="text-sm font-semibold">{title}</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleNewSearch} className="w-8 h-8 rounded-xl flex items-center justify-center text-muted-foreground bg-secondary hover:bg-accent transition-colors" title="Подбор сервиса">
            <Plus className="w-4 h-4" />
          </button>
          <ThemeToggle />
        </div>
      </div>
    );
  }

  // =========================== CATALOG ===========================
  if (phase === "catalog") {
    return (
      <div className="h-screen flex flex-col bg-background transition-colors duration-300">
        <MobileHeader title="Каталог" />
        <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-5">
            {catalogServices.map((s, i) => (
              <div key={s.id} className="flex animate-in fade-in duration-300" style={{ animationDelay: `${i * 40}ms` }}>
                <CatalogCard service={s} />
              </div>
            ))}
          </div>
        </div>

        <div className="shrink-0 border-t bg-card px-3 sm:px-5 py-3" style={{ paddingBottom: "env(safe-area-inset-bottom, 12px)" }}>
          <div className="flex items-center justify-between">
            <div className="hidden sm:block"><Logo /></div>
            <div className="flex-1 max-w-2xl mx-2 sm:mx-8 relative">
              {showSuggestions && (
                <div className="absolute bottom-full left-0 right-12 mb-2 flex gap-2 flex-wrap">
                  {["S3 хранилище до 3000 ₽", "VPS под 152-ФЗ", "Kubernetes"].map((hint) => (
                    <button
                      key={hint}
                      onClick={() => {
                        setInput(hint);
                        setShowSuggestions(false);
                      }}
                      className="px-3 py-1.5 text-xs font-medium rounded-full bg-card border hover:border-[#1DAFF7]/30 hover:text-[#1DAFF7] hover:bg-sky-50 dark:hover:bg-sky-900/20 transition-all shadow-sm"
                    >
                      {hint}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex gap-2 relative">
                <Search className="absolute left-4 top-3.5 sm:top-4 w-4 h-4 text-muted-foreground pointer-events-none z-10" />
                <Textarea
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    e.target.style.height = "auto";
                    e.target.style.height = e.target.scrollHeight + "px";
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleCatalogSearch(); } }}
                  placeholder="Подобрать облачный сервис"
                  rows={1}
                  className="flex-1 pl-10 text-foreground"
                />
                <Button onClick={handleCatalogSearch} disabled={!input.trim()} size="icon" className="w-10 h-10 sm:w-12 sm:h-12 shrink-0">
                  <Send className="w-4 h-4 sm:w-5 sm:h-5" />
                </Button>
              </div>
            </div>
            <div className="hidden sm:block"><RightButtons showNewChat={false} /></div>
          </div>
        </div>

        <style>{`
          .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
          .line-clamp-3 { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
          @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
          ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: transparent; }
          ::-webkit-scrollbar-thumb { background: hsl(var(--muted-foreground) / 0.3); border-radius: 3px; }
          ::-webkit-scrollbar-thumb:hover { background: hsl(var(--muted-foreground) / 0.5); }
        `}</style>
      </div>
    );
  }

  // =========================== CHAT ===========================
  if (phase === "chat") {
    return (
      <div className="h-screen flex flex-col bg-background transition-colors duration-300">
        <MobileHeader title={isNewSearch ? "Подбор сервиса" : "Чат"} />
        {resultsHistory.length > 0 && !isNewSearch && (
          <div className="shrink-0 hidden sm:flex items-center justify-end px-5 py-2 border-b">
            <button onClick={goToResults} className="text-muted-foreground hover:text-foreground transition-colors" title="Свернуть чат">
              <Minimize2 className="w-5 h-5" />
            </button>
          </div>
        )}
        {isNewSearch && (
          <div className="shrink-0 hidden sm:flex items-center px-5 py-2 border-b gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Подбор сервиса</span>
            <button onClick={goToResults} className="text-muted-foreground hover:text-foreground transition-colors ml-auto" title="Назад к результатам">
              <Minimize2 className="w-5 h-5" />
            </button>
          </div>
        )}
        <div ref={chatRef} className={`flex-1 overflow-y-auto px-3 sm:px-4 ${messages.length === 0 && isNewSearch ? "flex items-center justify-center py-0" : "py-6"}`}>
            <div className={`mx-auto ${messages.length === 0 && isNewSearch ? "" : "max-w-3xl space-y-4"}`}>
              {messages.length === 0 && isNewSearch ? (
                <div className="flex flex-col items-center text-center animate-in fade-in duration-300">
                  <Cloud className="w-10 h-10 text-[#1DAFF7] mb-4" />
                  <h3 className="text-base font-semibold mb-2">Подбор облачных сервисов</h3>
                  <p className="text-sm text-muted-foreground max-w-md mb-6">Опишите вашу задачу — система подберёт лучшие решения от российских провайдеров</p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {["S3 хранилище до 3000 ₽", "VPS под 152-ФЗ", "Kubernetes"].map((hint) => (
                      <button
                        key={hint}
                        onClick={() => { setInput(hint); }}
                        className="px-4 py-2 text-sm font-medium rounded-full bg-card border border-border hover:border-[#1DAFF7]/30 hover:text-[#1DAFF7] hover:bg-sky-50 dark:hover:bg-sky-900/20 transition-all shadow-sm"
                      >
                        {hint}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in duration-200`}>
                    <div className={`max-w-[90%] sm:max-w-[85%] lg:max-w-[70%] px-3 py-2 sm:px-4 sm:py-3 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-gradient-to-br from-[#1DAFF7] to-[#008ACD] text-white rounded-2xl rounded-br-md shadow-lg shadow-[#1DAFF7]/20"
                        : "bg-muted text-foreground rounded-2xl rounded-bl-md"
                    }`}>
                      {msg.text}
                    </div>
                  </div>
                ))
              )}
              {isLoading && (
                <div className="flex justify-start animate-in fade-in duration-200">
                  <Skeleton className="h-10 sm:h-12 w-3/4 rounded-2xl rounded-bl-md" />
                </div>
              )}
            </div>
          </div>

        <div className="shrink-0 border-t bg-card px-3 sm:px-5 py-3" style={{ paddingBottom: "env(safe-area-inset-bottom, 12px)" }}>
          <div className="flex items-center justify-between">
            <div className="hidden sm:block"><Logo /></div>
            <div className="flex-1 max-w-2xl mx-2 sm:mx-8 flex gap-3">
              <Textarea
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = e.target.scrollHeight + "px";
                }}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                placeholder="Опишите задачу..."
                disabled={isLoading}
                rows={1}
                className="flex-1 text-foreground"
              />
              <Button onClick={handleSend} disabled={isLoading || !input.trim()} size="icon" className="w-10 h-10 sm:w-12 sm:h-12 shrink-0">
                <Send className="w-4 h-4 sm:w-5 sm:h-5" />
              </Button>
            </div>
            <div className="hidden sm:block"><RightButtons showNewChat={true} /></div>
          </div>
        </div>
      </div>
    );
  }

  // =========================== RESULTS ===========================
  const currentSet = resultsHistory[selectedResultIdx];
  const hasHistory = resultsHistory.length > 0;
  const handleMobileSidebarToggle = () => setShowSearchHistory(v => !v);

  function handleSplitPointerDown(e: React.PointerEvent) {
    isDragging.current = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }
  function handleSplitPointerMove(e: React.PointerEvent) {
    if (!isDragging.current || !splitContainerRef.current) return;
    const rect = splitContainerRef.current.getBoundingClientRect();
    const y = e.clientY - rect.top;
    setSplitRatio(Math.max(0.15, Math.min(0.85, y / rect.height)));
  }
  function handleSplitPointerUp() {
    isDragging.current = false;
  }

  return (
    <div className="h-screen flex flex-col bg-background transition-colors duration-300">
      <MobileHeader title="Результаты" onToggleSidebar={hasHistory ? handleMobileSidebarToggle : undefined} />

      {/* MOBILE: split layout — top results, bottom chat + input */}
      <div ref={splitContainerRef} className="sm:hidden flex-1 flex flex-col overflow-hidden select-none">
        {/* Top: scrollable results */}
        <div className="overflow-y-auto min-h-0" style={{ flex: splitRatio }}>
          {currentSet && (
            <div className="p-3">
              <div className="grid grid-cols-1 gap-2">
                {currentSet.results.map((res, idx) => (
                  <div key={res.id} className="flex animate-in fade-in duration-400" style={{ animationDelay: `${idx * 120}ms` }}>
                    <ResultCardFull result={res} rank={idx + 1} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Draggable divider */}
        <div
          className="shrink-0 border-t flex items-center justify-center py-3 bg-card cursor-row-resize"
          style={{ touchAction: "none" }}
          onPointerDown={handleSplitPointerDown}
          onPointerMove={handleSplitPointerMove}
          onPointerUp={handleSplitPointerUp}
        >
          <div className="w-8 h-1 rounded-full bg-muted-foreground/30" />
        </div>

        {/* Bottom: scrollable chat messages */}
        <div ref={chatRef} className="overflow-y-auto px-3 py-2 space-y-2 min-h-0" style={{ flex: 1 - splitRatio }}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in duration-200`}>
              <div className={`max-w-[90%] px-3 py-2 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-gradient-to-br from-[#1DAFF7] to-[#008ACD] text-white rounded-2xl rounded-br-md"
                  : "bg-muted text-foreground rounded-2xl rounded-bl-md"
              }`}>
                {msg.text}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start animate-in fade-in duration-200">
              <Skeleton className="h-10 w-3/4 rounded-2xl rounded-bl-md" />
            </div>
          )}
        </div>

        {/* Input bar */}
        <div className="shrink-0 border-t bg-card px-3 py-2" style={{ paddingBottom: "env(safe-area-inset-bottom, 12px)" }}>
          <div className="flex gap-2">
            <Textarea
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = e.target.scrollHeight + "px";
              }}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="Уточните запрос..."
              disabled={isLoading}
              rows={1}
              className="flex-1 text-foreground"
            />
            <Button onClick={handleSend} disabled={isLoading || !input.trim()} size="icon" className="w-10 h-10 shrink-0">
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* DESKTOP: current layout — no changes */}
      <div className="hidden sm:flex flex-1 overflow-hidden relative">
        {hasHistory && (
          <>
            <div className={`shrink-0 border-r bg-card overflow-y-auto p-4 space-y-3 transition-all duration-200 ${showSearchHistory ? "w-60" : "w-auto"}`}>
              <div className="flex items-center gap-2">
                {!showSearchHistory && <div className="w-4" />}
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground whitespace-nowrap">Прошлые подборки</div>
                <button onClick={() => setShowSearchHistory(v => !v)} className="text-muted-foreground hover:text-foreground transition-colors ml-auto">
                  {showSearchHistory ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </button>
              </div>
              {showSearchHistory && resultsHistory.map((entry, idx) => (
                <button
                  key={idx}
                  onClick={() => { setSelectedResultIdx(idx); setMessages(resultsHistory[idx].messages); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                    idx === selectedResultIdx
                      ? "bg-[#1DAFF7]/10 text-[#1DAFF7] font-medium"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <div className="line-clamp-2">{entry.query}</div>
                </button>
              ))}
            </div>
          </>
        )}
        <div className="flex-1 overflow-y-auto">
          {currentSet && (
            <div className="max-w-6xl mx-auto p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-1 h-5 rounded-full bg-gradient-to-b from-[#1DAFF7] to-[#008ACD]" />
                <h2 className="text-base font-bold tracking-tight">Результаты</h2>
                {selectedResultIdx > 0 && (
                  <span className="text-xs text-muted-foreground ml-2">(архивный)</span>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {currentSet.results.map((res, idx) => (
                  <div key={res.id} className="flex animate-in fade-in duration-400" style={{ animationDelay: `${idx * 120}ms` }}>
                    <ResultCardFull result={res} rank={idx + 1} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* DESKTOP: bottom bar — no changes */}
      <div
        className="hidden sm:block shrink-0 border-t bg-card px-5 py-3 relative"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 12px)" }}
        onMouseEnter={() => messages.length > 0 && !isNewSearch && setShowHistory(true)}
        onMouseLeave={() => setShowHistory(false)}
      >
        <div className="flex items-center justify-between">
          <Logo />
          <div className="flex-1 max-w-2xl mx-8">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                {showHistory && messages.length > 0 && (
                  <HistoryOverlay
                    messages={messages}
                    onExpand={showFullChat}
                  />
                )}
                <Textarea
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    e.target.style.height = "auto";
                    e.target.style.height = e.target.scrollHeight + "px";
                  }}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  placeholder="Уточните запрос..."
                  disabled={isLoading}
                  rows={1}
                  className="flex-1 text-foreground"
                />
              </div>
              <Button onClick={handleSend} disabled={isLoading || !input.trim()} size="icon" className="w-12 h-12 shrink-0">
                <Send className="w-5 h-5" />
              </Button>
            </div>
          </div>
          <RightButtons showNewChat={true} />
        </div>
      </div>

      {/* Mobile sidebar overlay */}
      {showSearchHistory && (
        <div className="sm:hidden fixed inset-0 z-50" onClick={() => setShowSearchHistory(false)}>
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
          <div className="absolute left-0 top-0 bottom-0 w-64 bg-card border-r shadow-2xl p-4 space-y-3 overflow-y-auto animate-in slide-in-from-left duration-200" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Прошлые подборки</div>
              <button onClick={() => setShowSearchHistory(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
            </div>
            {resultsHistory.map((entry, idx) => (
              <button
                key={idx}
                onClick={() => { setSelectedResultIdx(idx); setMessages(resultsHistory[idx].messages); setShowSearchHistory(false); }}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                  idx === selectedResultIdx
                    ? "bg-[#1DAFF7]/10 text-[#1DAFF7] font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <div className="line-clamp-2">{entry.query}</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
