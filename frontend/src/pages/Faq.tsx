import type { ReactNode } from "react";
import { Nav, PageFooter } from "./Nav";
import { navigate } from "../router";
import { AdSlot } from "../components/AdSlot";

type Qa = { q: string; a: ReactNode };

const QAS: Qa[] = [
  {
    q: "予測の精度はどれくらいですか？",
    a: (
      <>
        試合のカテゴリや信頼度ランクによって大きく異なります。信頼度HIGHのカードでは比較的高い的中率、
        信頼度LOW（接戦カード）では半々に近い結果になる傾向があります。
        具体的な数値はサイト内の「的中率」タブで過去の予測結果と合わせて常時公開しています。
        格闘技は予測困難な競技であり、どんなAIでも100%当てることは不可能です。
        あくまで参考情報としてご利用ください。
      </>
    ),
  },
  {
    q: "どの団体の試合を予測できますか？",
    a: (
      <>
        現在はUFC（Ultimate Fighting Championship）とRIZIN（日本のRIZIN Fighting Federation）に対応しています。
        UFCはUFCstats.comの公式データ、RIZINはSherdog.comの選手ページから選手情報を取得しています。
        Bellator、ONE Championship、PFL等は現時点では未対応です。
      </>
    ),
  },
  {
    q: "選手名はどう入力すればいいですか？",
    a: (
      <>
        日本語（漢字・ひらがな・カタカナ）、英語の全てに対応しています。
        例えば「朝倉未来」「あさくらみくる」「Mikuru Asakura」のどれでも検索できます。
        外国人選手の場合は「シェイドゥラエフ」「Shamil Gaziev」のようにカタカナ・英語のどちらでも可。
        入力欄に2文字以上入れるとオートコンプリート候補が表示されるので、そこから選択してください。
      </>
    ),
  },
  {
    q: "大会の全試合を一括で予測できますか？",
    a: (
      <>
        はい、できます。トップページの「大会」タブを開くと、開催予定のUFC・RIZIN大会一覧が表示されます。
        カードをクリックすると、その大会の全試合（メインからプレリムまで）のAI予測を一覧で表示します。
        noteで公開している大会別予測レポートは、この機能を使って自動生成しています。
      </>
    ),
  },
  {
    q: "有料ですか？",
    a: (
      <>
        予測ツール本体は完全無料でご利用いただけます。広告表示と、格闘技関連の配信サービス・用品への
        アフィリエイトリンクで運営しており、サイトのご利用にあたって料金は一切発生しません。
        note上で公開している事前予測レポートも、現時点では全て無料公開しています。
      </>
    ),
  },
  {
    q: "予測結果をX（Twitter）でシェアしたいのですが？",
    a: (
      <>
        予測結果の右下に「Xでシェア」ボタンと「画像保存」ボタンがあります。
        勝率・決着方法・予測根拠を含むOGPサイズの画像を自動生成できます。
        Web Share APIに対応したスマートフォンでは画像付きで直接投稿でき、
        PCではテキスト＋サイトURLを含むX投稿画面が開きます。
      </>
    ),
  },
  {
    q: "選手のスタッツが公式と違うのですが？",
    a: (
      <>
        UFC選手は UFCstats.com のスタッツをそのまま表示しています（ただし体重表記など一部整形）。
        RIZIN選手については Sherdog.com から直接取得できるのは戦績のみのため、
        打撃・テイクダウン・サブミッション等のスタッツは戦績から推定しています。
        推定値を使っている場合は予測根拠欄に「※スタッツは戦績から推定」と明示しているほか、
        そのカードの信頼度ランクも自動的にダウングレードされます。
      </>
    ),
  },
  {
    q: "的中率タブに出てくる予測はどうやって集めているのですか？",
    a: (
      <>
        予測ツール経由で行われた全ての予測が自動的にサーバーに保存されます。
        試合終了後にユーザー側で「選手A勝利」「選手B勝利」のボタンを押して結果を記録することで、
        信頼度別の的中率が集計されます。結果未入力の試合は「未入力」として一覧に残ります。
        2時間ごとにGitHub上へバックアップも取られるため、サーバー再起動で履歴が失われることはありません。
      </>
    ),
  },
  {
    q: "オッズは見られますか？賭け事に使えますか？",
    a: (
      <>
        ブックメーカーのオッズは表示していません。あくまで「データから見た確率」を算出するツールです。
        本サイトは日本国内向けに作られており、オンラインカジノ・ブックメーカー等のギャンブル行為への
        利用を想定・推奨していません。格闘技観戦の楽しみ方を広げる目的でご利用ください。
      </>
    ),
  },
  {
    q: "更新はされていますか？",
    a: (
      <>
        UFCは大会開催ごとに選手データが自動更新されます。RIZIN選手のキャッシュは
        12時間おきに対戦相手平均勝率が再計算されるなど、継続的にメンテナンスしています。
        機能追加・不具合修正の履歴はGitHubリポジトリの進捗ドキュメントに記録しています。
        改善要望はX（
        <a
          href="https://x.com/fight_predict_"
          target="_blank"
          rel="noopener noreferrer"
        >
          @fight_predict_
        </a>
        ）までお送りください。
      </>
    ),
  },
];

export function Faq() {
  return (
    <div className="app site-page">
      <Nav current="/faq" />
      <main className="content-page">
        <header className="content-hero">
          <h1>よくある質問（FAQ）</h1>
          <p>
            FIGHT PREDICTの使い方・予測精度・データソースについて、よく寄せられる質問をまとめました。
            ここに答えがない内容は、X（
            <a
              href="https://x.com/fight_predict_"
              target="_blank"
              rel="noopener noreferrer"
            >
              @fight_predict_
            </a>
            ）までお気軽にお問い合わせください。
          </p>
        </header>

        <section className="faq-list">
          {QAS.map((qa, idx) => (
            <div key={idx} className="faq-item">
              <h2 className="faq-q">
                <span className="faq-q-mark">Q.</span>
                {qa.q}
              </h2>
              <div className="faq-a">
                <span className="faq-a-mark">A.</span>
                <div>{qa.a}</div>
              </div>
            </div>
          ))}
        </section>

        <AdSlot placement="content-bottom" />

        <section className="content-block">
          <h2>他に知りたいことは？</h2>
          <p>
            予測ロジックの詳細は専用ページで解説しています。
          </p>
          <button
            className="article-cta-btn"
            onClick={() => navigate("/how-it-works")}
          >
            予測ロジックの仕組みを見る
          </button>
          <button
            className="article-cta-btn secondary"
            onClick={() => navigate("/articles")}
          >
            大会別の予測記事を見る
          </button>
        </section>
      </main>
      <PageFooter />
    </div>
  );
}
