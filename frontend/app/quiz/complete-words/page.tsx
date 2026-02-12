import { CompleteTheWordsPrompt } from '../../../components/CompleteTheWordsPrompt';

const paragraph = `Ocean currents are powerful streams of water that move through the world's oceans and play a major role in shaping global weather patterns. [T][h][e][s][e] currents transport warm [a][n][d] cold water across [v][a][s][t] distances, [h][e][l][p][i][n][g] to [d][i][s][t][r][i][b][u][t][e] heat [a][r][o][u][n][d] the [p][l][a][n][e][t].`;

export default function CompleteWordsPage() {
  return (
    <main className="min-h-dvh bg-gradient-to-b from-slate-100 via-slate-50 to-white px-4 py-12 text-slate-900 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 dark:text-slate-100">
      <div className="mx-auto w-full max-w-5xl">
        <h1 className="mb-3 text-3xl font-bold tracking-tight md:text-4xl">Fill in the missing letters in the paragraph.</h1>
        <p className="mb-8 text-sm text-slate-500 dark:text-slate-400">
          클릭 후 타이핑하면 빈칸이 순차적으로 채워집니다.
        </p>
        <CompleteTheWordsPrompt paragraph={paragraph} />
      </div>
    </main>
  );
}
