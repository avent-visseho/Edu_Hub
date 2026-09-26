'use client';

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { useAccessibilite } from '@/lib/accessibilite';
import { formaterNombre } from '@/lib/utils';

/**
 * Palette catégorielle bâtie sur l'identité : le bleu profond du logo, l'or de
 * ses pages, le vert et le rouge du drapeau, le bleu vif du sigle.
 *
 * L'ordre n'est pas celui de l'identité mais celui du contraste : les deux
 * bleus de la marque sont volontairement séparés, car un camembert à deux parts
 * — la parité filles / garçons, par exemple — prend les deux premières couleurs
 * et deux bleus voisins y seraient indistinguables.
 *
 * Les valeurs sont figées et non tirées des jetons de thème : un graphique doit
 * garder les mêmes couleurs en clair, en sombre et à l'impression, sans quoi
 * une légende imprimée ne correspondrait plus à l'écran. Elles ont été
 * choisies lisibles sur les deux fonds et distinguables par les principales
 * formes de daltonisme.
 */
export const COULEURS = {
  bleu: '#00489c', // bleu profond — « Edu »
  or: '#f0b000', // or des pages du livre
  vert: '#008751', // vert du drapeau
  bleuVif: '#0c78d8', // bleu vif — « Hub »
  rouge: '#e8112d', // rouge du drapeau
  violet: '#7c3aed',
  cyan: '#0891b2', // pour les séries longues
  ardoise: '#54677f', // pour les restes et les « autres »
} as const;

export const PALETTE = [
  COULEURS.bleu,
  COULEURS.or,
  COULEURS.vert,
  COULEURS.bleuVif,
  COULEURS.rouge,
  COULEURS.violet,
  COULEURS.cyan,
  COULEURS.ardoise,
];

const STYLE_INFOBULLE = {
  backgroundColor: 'rgb(var(--fond-carte))',
  border: '1px solid rgb(var(--bordure))',
  borderRadius: '0.5rem',
  color: 'rgb(var(--texte))',
  fontSize: '0.8125rem',
  padding: '0.5rem 0.75rem',
};

/**
 * Repli textuel affiché lorsque l'économie de données est active : un tableau
 * reste parfaitement lisible et ne coûte presque rien à afficher.
 */
function TableauDeRepli({
  donnees,
  cleAbscisse,
  series,
  titre,
}: {
  donnees: Array<Record<string, unknown>>;
  cleAbscisse: string;
  series: Array<{ cle: string; libelle: string }>;
  titre: string;
}) {
  return (
    <div className="defilement-fin overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="sr-only">{titre}</caption>
        <thead>
          <tr className="surface-douce">
            <th scope="col" className="border-b px-3 py-2 text-left text-xs uppercase texte-doux">
              Libellé
            </th>
            {series.map((serie) => (
              <th
                key={serie.cle}
                scope="col"
                className="border-b px-3 py-2 text-right text-xs uppercase texte-doux"
              >
                {serie.libelle}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {donnees.map((ligne, index) => (
            <tr key={`${String(ligne[cleAbscisse])}-${index}`} className="border-b last:border-0">
              <td className="px-3 py-2">{String(ligne[cleAbscisse] ?? '—')}</td>
              {series.map((serie) => (
                <td key={serie.cle} className="px-3 py-2 text-right tabular-nums">
                  {formaterNombre(Number(ligne[serie.cle] ?? 0), 1)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface ProprietesGraphique {
  donnees: Array<Record<string, unknown>>;
  cleAbscisse: string;
  series: Array<{ cle: string; libelle: string; couleur?: string }>;
  titre: string;
  hauteur?: number;
  /** Suffixe ajouté aux valeurs dans l'infobulle. */
  unite?: string;
  /** Longueur au-delà de laquelle les libellés d'abscisse sont tronqués. */
  longueurEtiquette?: number;
}

/** Raccourcit un libellé d'axe tout en gardant l'information utile. */
function raccourcir(valeur: unknown, longueur: number): string {
  const texte = String(valeur ?? '');
  return texte.length <= longueur ? texte : `${texte.slice(0, longueur - 1)}…`;
}

export function GraphiqueBarres({
  donnees,
  cleAbscisse,
  series,
  titre,
  hauteur = 280,
  unite,
  longueurEtiquette = 18,
}: ProprietesGraphique) {
  const { economieDonnees } = useAccessibilite();
  if (economieDonnees || donnees.length === 0) {
    return (
      <TableauDeRepli donnees={donnees} cleAbscisse={cleAbscisse} series={series} titre={titre} />
    );
  }

  return (
    <figure className="w-full">
      <figcaption className="sr-only">{titre}</figcaption>
      <ResponsiveContainer width="100%" height={hauteur}>
        <BarChart data={donnees} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--bordure))" vertical={false} />
          <XAxis
            dataKey={cleAbscisse}
            tick={{ fontSize: 11, fill: 'rgb(var(--texte-doux))' }}
            stroke="rgb(var(--bordure))"
            interval={0}
            angle={donnees.length > 8 ? -35 : 0}
            textAnchor={donnees.length > 8 ? 'end' : 'middle'}
            height={donnees.length > 8 ? 70 : 30}
            tickFormatter={(valeur) => raccourcir(valeur, longueurEtiquette)}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'rgb(var(--texte-doux))' }}
            stroke="rgb(var(--bordure))"
            width={48}
          />
          <Tooltip
            contentStyle={STYLE_INFOBULLE}
            formatter={(valeur: number) =>
              `${formaterNombre(valeur, 1)}${unite ? ` ${unite}` : ''}`
            }
          />
          {series.length > 1 ? <Legend wrapperStyle={{ fontSize: '0.8125rem' }} /> : null}
          {series.map((serie, index) => (
            <Bar
              key={serie.cle}
              dataKey={serie.cle}
              name={serie.libelle}
              fill={serie.couleur ?? PALETTE[index % PALETTE.length]}
              radius={[4, 4, 0, 0]}
              maxBarSize={48}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </figure>
  );
}

export function GraphiqueLignes({
  donnees,
  cleAbscisse,
  series,
  titre,
  hauteur = 280,
  unite,
}: ProprietesGraphique) {
  const { economieDonnees } = useAccessibilite();
  if (economieDonnees || donnees.length === 0) {
    return (
      <TableauDeRepli donnees={donnees} cleAbscisse={cleAbscisse} series={series} titre={titre} />
    );
  }

  return (
    <figure className="w-full">
      <figcaption className="sr-only">{titre}</figcaption>
      <ResponsiveContainer width="100%" height={hauteur}>
        <LineChart data={donnees} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--bordure))" vertical={false} />
          <XAxis
            dataKey={cleAbscisse}
            tick={{ fontSize: 11, fill: 'rgb(var(--texte-doux))' }}
            stroke="rgb(var(--bordure))"
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'rgb(var(--texte-doux))' }}
            stroke="rgb(var(--bordure))"
            width={48}
          />
          <Tooltip
            contentStyle={STYLE_INFOBULLE}
            formatter={(valeur: number) =>
              `${formaterNombre(valeur, 1)}${unite ? ` ${unite}` : ''}`
            }
          />
          {series.length > 1 ? <Legend wrapperStyle={{ fontSize: '0.8125rem' }} /> : null}
          {series.map((serie, index) => (
            <Line
              key={serie.cle}
              type="monotone"
              dataKey={serie.cle}
              name={serie.libelle}
              stroke={serie.couleur ?? PALETTE[index % PALETTE.length]}
              strokeWidth={2.5}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </figure>
  );
}

export function GraphiqueSecteurs({
  donnees,
  cleLibelle,
  cleValeur,
  titre,
  hauteur = 260,
}: {
  donnees: Array<Record<string, unknown>>;
  cleLibelle: string;
  cleValeur: string;
  titre: string;
  hauteur?: number;
}) {
  const { economieDonnees } = useAccessibilite();
  if (economieDonnees || donnees.length === 0) {
    return (
      <TableauDeRepli
        donnees={donnees}
        cleAbscisse={cleLibelle}
        series={[{ cle: cleValeur, libelle: 'Effectif' }]}
        titre={titre}
      />
    );
  }

  return (
    <figure className="w-full">
      <figcaption className="sr-only">{titre}</figcaption>
      <ResponsiveContainer width="100%" height={hauteur}>
        <PieChart>
          <Pie
            data={donnees}
            dataKey={cleValeur}
            nameKey={cleLibelle}
            cx="50%"
            cy="45%"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
            isAnimationActive={false}
          >
            {donnees.map((_, index) => (
              <Cell key={index} fill={PALETTE[index % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={STYLE_INFOBULLE}
            formatter={(valeur: number) => formaterNombre(valeur)}
          />
          <Legend wrapperStyle={{ fontSize: '0.8125rem' }} />
        </PieChart>
      </ResponsiveContainer>
    </figure>
  );
}
