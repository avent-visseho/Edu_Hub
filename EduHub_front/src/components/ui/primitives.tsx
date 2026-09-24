'use client';

import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from 'react';

import { cn } from '@/lib/utils';

// ------------------------------------------------------------------
//  Bouton
// ------------------------------------------------------------------

type VarianteBouton = 'principal' | 'secondaire' | 'discret' | 'danger' | 'fantome';
type TailleBouton = 'sm' | 'md' | 'lg';

const VARIANTES: Record<VarianteBouton, string> = {
  principal:
    'bg-[rgb(var(--accent))] text-[rgb(var(--accent-contraste))] hover:brightness-110 shadow-sm',
  secondaire:
    'surface text-[rgb(var(--texte))] hover:bg-[rgb(var(--fond-doux))] border',
  discret: 'surface-douce text-[rgb(var(--texte))] hover:brightness-95 border border-transparent',
  danger: 'bg-[rgb(var(--danger))] text-white hover:brightness-110 shadow-sm',
  fantome: 'text-[rgb(var(--texte))] hover:bg-[rgb(var(--fond-doux))]',
};

const TAILLES: Record<TailleBouton, string> = {
  sm: 'h-9 px-3 text-sm gap-1.5',
  md: 'h-11 px-4 gap-2',
  lg: 'h-13 px-6 text-lg gap-2.5',
};

interface ProprietesBouton extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: VarianteBouton;
  taille?: TailleBouton;
  chargement?: boolean;
  /** Icône affichée avant le libellé. */
  icone?: ReactNode;
}

export const Bouton = forwardRef<HTMLButtonElement, ProprietesBouton>(function Bouton(
  { className, variante = 'principal', taille = 'md', chargement, icone, children, disabled, ...reste },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || chargement}
      aria-busy={chargement || undefined}
      className={cn(
        'inline-flex items-center justify-center rounded-lg font-medium transition',
        'disabled:cursor-not-allowed disabled:opacity-55',
        VARIANTES[variante],
        TAILLES[taille],
        className,
      )}
      {...reste}
    >
      {chargement ? (
        <span
          aria-hidden
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent"
        />
      ) : (
        icone
      )}
      {children}
    </button>
  );
});

// ------------------------------------------------------------------
//  Carte
// ------------------------------------------------------------------

export function Carte({
  className,
  children,
  ...reste
}: { className?: string; children: ReactNode } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('surface rounded-xl shadow-carte', className)} {...reste}>
      {children}
    </div>
  );
}

export function EnteteCarte({
  titre,
  description,
  action,
  className,
}: {
  titre: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4',
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-lg font-semibold leading-tight">{titre}</h2>
        {description ? <p className="mt-1 text-sm texte-doux">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function CorpsCarte({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('p-5', className)}>{children}</div>;
}

// ------------------------------------------------------------------
//  Badge
// ------------------------------------------------------------------

type TonBadge = 'neutre' | 'succes' | 'alerte' | 'danger' | 'info';

const TONS: Record<TonBadge, string> = {
  neutre: 'surface-douce texte-doux border',
  succes: 'bg-[rgb(var(--succes))]/12 text-[rgb(var(--succes))] border-[rgb(var(--succes))]/35',
  alerte: 'bg-[rgb(var(--alerte))]/14 text-[rgb(var(--alerte))] border-[rgb(var(--alerte))]/40',
  danger: 'bg-[rgb(var(--danger))]/12 text-[rgb(var(--danger))] border-[rgb(var(--danger))]/35',
  info: 'bg-[rgb(var(--accent))]/12 text-[rgb(var(--accent))] border-[rgb(var(--accent))]/35',
};

export function Badge({
  ton = 'neutre',
  children,
  className,
}: {
  ton?: TonBadge;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        TONS[ton],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Choisit automatiquement le ton d'un badge selon un statut métier. */
export function tonDuStatut(statut: string | null | undefined): TonBadge {
  if (!statut) return 'neutre';
  const valeur = statut.toUpperCase();
  if (/ADMIS$|VALID|PUBLI|ATTRIBU|ACCEPT|TERMIN|RETENU|FAVORABLE|ACTIF|EMIS/.test(valeur)) {
    return valeur.startsWith('NON_') ? 'danger' : 'succes';
  }
  if (/REJET|EXCLU|ANNUL|ECHEC|DEFAVORABLE|SUSPEND|CRITIQUE|NON_ADMIS/.test(valeur)) {
    return 'danger';
  }
  if (/ATTENTE|INCOMPLET|EN_ETUDE|EN_COURS|BROUILLON|PREPARATION|SOUMIS|RETARD/.test(valeur)) {
    return 'alerte';
  }
  return 'info';
}

// ------------------------------------------------------------------
//  Champs de formulaire
// ------------------------------------------------------------------

interface ProprietesChamp extends InputHTMLAttributes<HTMLInputElement> {
  etiquette: string;
  aide?: string;
  erreur?: string;
  /** Masque visuellement l'étiquette sans la retirer aux lecteurs d'écran. */
  etiquetteMasquee?: boolean;
}

export const Champ = forwardRef<HTMLInputElement, ProprietesChamp>(function Champ(
  { etiquette, aide, erreur, etiquetteMasquee, className, id, ...reste },
  ref,
) {
  const identifiant = id ?? `champ-${etiquette.toLowerCase().replace(/\s+/g, '-')}`;
  const idAide = aide ? `${identifiant}-aide` : undefined;
  const idErreur = erreur ? `${identifiant}-erreur` : undefined;

  return (
    <div className="space-y-1.5">
      <label
        htmlFor={identifiant}
        className={cn('block text-sm font-medium', etiquetteMasquee && 'sr-only')}
      >
        {etiquette}
        {reste.required ? <span className="text-[rgb(var(--danger))]"> *</span> : null}
      </label>
      <input
        ref={ref}
        id={identifiant}
        aria-describedby={[idAide, idErreur].filter(Boolean).join(' ') || undefined}
        aria-invalid={erreur ? true : undefined}
        className={cn(
          'w-full rounded-lg border bg-[rgb(var(--fond-carte))] px-3 py-2.5',
          'placeholder:text-[rgb(var(--texte-doux))]/70',
          erreur && 'border-[rgb(var(--danger))]',
          className,
        )}
        {...reste}
      />
      {aide ? (
        <p id={idAide} className="text-xs texte-doux">
          {aide}
        </p>
      ) : null}
      {erreur ? (
        <p id={idErreur} role="alert" className="text-xs font-medium text-[rgb(var(--danger))]">
          {erreur}
        </p>
      ) : null}
    </div>
  );
});

interface ProprietesSelection extends SelectHTMLAttributes<HTMLSelectElement> {
  etiquette: string;
  options: Array<{ valeur: string; libelle: string }>;
  aide?: string;
  etiquetteMasquee?: boolean;
}

export const Selection = forwardRef<HTMLSelectElement, ProprietesSelection>(function Selection(
  { etiquette, options, aide, etiquetteMasquee, className, id, ...reste },
  ref,
) {
  const identifiant = id ?? `selection-${etiquette.toLowerCase().replace(/\s+/g, '-')}`;
  return (
    <div className="space-y-1.5">
      <label
        htmlFor={identifiant}
        className={cn('block text-sm font-medium', etiquetteMasquee && 'sr-only')}
      >
        {etiquette}
      </label>
      <select
        ref={ref}
        id={identifiant}
        className={cn(
          'w-full rounded-lg border bg-[rgb(var(--fond-carte))] px-3 py-2.5',
          className,
        )}
        {...reste}
      >
        {options.map((option) => (
          <option key={option.valeur} value={option.valeur}>
            {option.libelle}
          </option>
        ))}
      </select>
      {aide ? <p className="text-xs texte-doux">{aide}</p> : null}
    </div>
  );
});

// ------------------------------------------------------------------
//  Interrupteur
// ------------------------------------------------------------------

export function Interrupteur({
  etiquette,
  description,
  actif,
  onChange,
  icone,
}: {
  etiquette: string;
  description?: string;
  actif: boolean;
  onChange: () => void;
  icone?: ReactNode;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={actif}
      onClick={onChange}
      className={cn(
        'flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2.5 text-left transition',
        actif
          ? 'border-[rgb(var(--accent))] bg-[rgb(var(--accent))]/10'
          : 'surface hover:bg-[rgb(var(--fond-doux))]',
      )}
    >
      <span className="flex min-w-0 items-center gap-2.5">
        {icone ? <span aria-hidden className="shrink-0">{icone}</span> : null}
        <span className="min-w-0">
          <span className="block text-sm font-medium">{etiquette}</span>
          {description ? <span className="block text-xs texte-doux">{description}</span> : null}
        </span>
      </span>
      <span
        aria-hidden
        className={cn(
          'relative h-6 w-11 shrink-0 rounded-full border transition',
          actif ? 'bg-[rgb(var(--accent))]' : 'surface-douce',
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all',
            actif ? 'left-[1.55rem]' : 'left-0.5',
          )}
        />
      </span>
    </button>
  );
}

// ------------------------------------------------------------------
//  États
// ------------------------------------------------------------------

export function Chargement({ libelle = 'Chargement en cours…' }: { libelle?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 p-8 texte-doux">
      <span
        aria-hidden
        className="h-5 w-5 animate-spin rounded-full border-2 border-current border-r-transparent"
      />
      <span>{libelle}</span>
    </div>
  );
}

export function Squelette({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn('animate-pulsation rounded surface-douce', className ?? 'h-4 w-full')}
    />
  );
}

export function EtatVide({
  titre,
  description,
  icone,
  action,
}: {
  titre: string;
  description?: string;
  icone?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
      {icone ? (
        <span aria-hidden className="texte-doux opacity-70">
          {icone}
        </span>
      ) : null}
      <p className="text-base font-medium">{titre}</p>
      {description ? <p className="max-w-md text-sm texte-doux">{description}</p> : null}
      {action}
    </div>
  );
}

export function MessageErreur({ erreur }: { erreur: unknown }) {
  const message =
    erreur instanceof Error ? erreur.message : "Une erreur inattendue s'est produite.";
  return (
    <div
      role="alert"
      className="rounded-lg border border-[rgb(var(--danger))]/40 bg-[rgb(var(--danger))]/8 px-4 py-3 text-sm"
    >
      <p className="font-medium text-[rgb(var(--danger))]">{message}</p>
    </div>
  );
}
