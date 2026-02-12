'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { useCallback, useMemo, useRef, useState } from 'react';

type Blank = {
  id: number;
  answer: string;
  index: number;
};

type CharToken =
  | { type: 'text'; value: string; key: string }
  | { type: 'blank'; blankId: number; key: string };

interface CompleteTheWordsPromptProps {
  paragraph: string;
  className?: string;
}

const BLANK_PATTERN = /\[(?<answer>[A-Za-z])\]/g;

export function CompleteTheWordsPrompt({ paragraph, className }: CompleteTheWordsPromptProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const { tokens, blanks } = useMemo(() => {
    const nextTokens: CharToken[] = [];
    const nextBlanks: Blank[] = [];

    let cursor = 0;
    let blankId = 0;

    for (const match of paragraph.matchAll(BLANK_PATTERN)) {
      const matchIndex = match.index ?? 0;
      const answer = match.groups?.answer ?? '';

      const textChunk = paragraph.slice(cursor, matchIndex);
      for (const ch of textChunk) {
        nextTokens.push({ type: 'text', value: ch, key: `t-${nextTokens.length}` });
      }

      nextBlanks.push({
        id: blankId,
        answer: answer.toLowerCase(),
        index: nextTokens.length,
      });
      nextTokens.push({ type: 'blank', blankId, key: `b-${blankId}` });

      blankId += 1;
      cursor = matchIndex + match[0].length;
    }

    const tail = paragraph.slice(cursor);
    for (const ch of tail) {
      nextTokens.push({ type: 'text', value: ch, key: `t-${nextTokens.length}` });
    }

    return { tokens: nextTokens, blanks: nextBlanks };
  }, [paragraph]);

  const [values, setValues] = useState<Record<number, string>>({});
  const [activeBlankId, setActiveBlankId] = useState<number | null>(blanks[0]?.id ?? null);

  const totalCount = blanks.length;
  const filledCount = useMemo(
    () => blanks.reduce((acc, blank) => (values[blank.id] ? acc + 1 : acc), 0),
    [blanks, values],
  );

  const completionRate = totalCount === 0 ? 0 : Math.round((filledCount / totalCount) * 100);

  const focusHiddenInput = useCallback(() => {
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  const moveToNextBlank = useCallback(
    (currentId: number) => {
      const next = blanks.find((blank) => blank.id > currentId && !values[blank.id]);
      if (next) {
        setActiveBlankId(next.id);
        return;
      }

      const firstEmpty = blanks.find((blank) => !values[blank.id]);
      setActiveBlankId(firstEmpty?.id ?? currentId);
    },
    [blanks, values],
  );

  const handleBlankClick = useCallback(
    (blankId: number) => {
      setActiveBlankId(blankId);
      focusHiddenInput();
    },
    [focusHiddenInput],
  );

  const handleInput = useCallback(
    (raw: string) => {
      if (activeBlankId === null) return;
      const normalized = raw.replace(/[^a-zA-Z]/g, '').slice(-1).toLowerCase();
      if (!normalized) return;

      setValues((prev) => ({ ...prev, [activeBlankId]: normalized }));
      moveToNextBlank(activeBlankId);
    },
    [activeBlankId, moveToNextBlank],
  );

  const handleBackspace = useCallback(() => {
    if (activeBlankId === null) return;

    if (values[activeBlankId]) {
      setValues((prev) => ({ ...prev, [activeBlankId]: '' }));
      return;
    }

    const prevCandidates = blanks.filter((blank) => blank.id < activeBlankId);
    const prev = prevCandidates[prevCandidates.length - 1];
    if (!prev) return;

    setActiveBlankId(prev.id);
    setValues((prevValues) => ({ ...prevValues, [prev.id]: '' }));
  }, [activeBlankId, blanks, values]);

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={[
        'w-full rounded-2xl border border-slate-200 bg-white/95 p-6 shadow-xl shadow-slate-900/5 backdrop-blur md:p-8',
        'dark:border-slate-700 dark:bg-slate-900/90 dark:shadow-black/20',
        className ?? '',
      ].join(' ')}
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Complete the words
        </h2>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {filledCount}/{totalCount} · {completionRate}%
        </span>
      </div>

      <div className="mb-5 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <motion.div
          className="h-full bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500"
          animate={{ width: `${completionRate}%` }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
        />
      </div>

      <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
        빈칸을 클릭하고 영문자를 입력하세요. 한 글자를 채우면 다음 빈칸으로 자동 이동합니다.
      </p>

      <div
        role="group"
        aria-label="빈칸 완성 문제"
        className="flex flex-wrap items-end gap-x-1 gap-y-2 text-[clamp(1.05rem,2.8vw,2rem)] leading-relaxed text-slate-700 dark:text-slate-200"
      >
        {tokens.map((token, idx) => {
          if (token.type === 'text') {
            return (
              <span key={token.key} className={token.value === ' ' ? 'mx-[0.14em]' : ''}>
                {token.value}
              </span>
            );
          }

          const blank = blanks[token.blankId];
          const value = values[blank.id] ?? '';
          const isActive = activeBlankId === blank.id;
          const isCorrect = value.length === 1 && value === blank.answer;
          const isWrong = value.length === 1 && value !== blank.answer;

          return (
            <button
              key={token.key}
              type="button"
              aria-label={`${idx + 1}번째 빈칸`}
              onClick={() => handleBlankClick(blank.id)}
              className={[
                'relative inline-flex h-[1.55em] w-[1.25em] items-center justify-center rounded-md border text-[0.92em] font-medium uppercase',
                'transition-all duration-200 ease-out focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400',
                isActive
                  ? 'border-indigo-400 bg-indigo-50 text-indigo-700 shadow-md shadow-indigo-200/60 dark:bg-indigo-900/30 dark:text-indigo-200'
                  : 'border-slate-300 bg-slate-50 text-slate-700 hover:border-slate-400 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200',
                isCorrect ? 'border-emerald-400 bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200' : '',
                isWrong ? 'border-rose-400 bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-200' : '',
              ].join(' ')}
            >
              <AnimatePresence mode="wait" initial={false}>
                <motion.span
                  key={value || `empty-${blank.id}`}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -3 }}
                  transition={{ duration: 0.18 }}
                  className="pointer-events-none"
                >
                  {value || '·'}
                </motion.span>
              </AnimatePresence>
            </button>
          );
        })}
      </div>

      {/* 키보드 입력을 일관되게 받기 위한 숨김 입력 필드 */}
      <input
        ref={inputRef}
        type="text"
        inputMode="text"
        autoCapitalize="none"
        autoCorrect="off"
        spellCheck={false}
        className="sr-only"
        onKeyDown={(event) => {
          if (event.key === 'Backspace') {
            event.preventDefault();
            handleBackspace();
            return;
          }

          if (event.key.length === 1) {
            event.preventDefault();
            handleInput(event.key);
          }
        }}
        onBlur={() => setTimeout(() => inputRef.current?.focus(), 0)}
      />

      <button
        type="button"
        className="mt-6 inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors duration-200 hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
        onClick={focusHiddenInput}
      >
        입력 시작
      </button>
    </motion.section>
  );
}
