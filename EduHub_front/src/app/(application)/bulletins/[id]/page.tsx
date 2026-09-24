'use client';

import { useQuery } from '@tanstack/react-query';
import { Printer, Volume2 } from 'lucide-react';
import { useParams } from 'next/navigation';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeDescriptive, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  MessageErreur,
  tonDuStatut,
} from '@/components/ui/primitives';
import { useAccessibilite } from '@/lib/accessibilite';
import { api } from '@/lib/api';
import { formaterNote, humaniser } from '@/lib/utils';
import type { BulletinDetail } from '@/types/api';

export default function PageBulletin() {
  const parametres = useParams<{ id: string }>();
  const { lectureVocale, lire } = useAccessibilite();

  const bulletin = useQuery({
    queryKey: ['bulletin', parametres.id],
    queryFn: () => api.get<BulletinDetail>(`/bulletins/${parametres.id}/detail`),
  });

  if (bulletin.isLoading) return <Chargement libelle="Ouverture du bulletin…" />;
  if (bulletin.isError) return <MessageErreur erreur={bulletin.error} />;

  const donnees = bulletin.data!;

  const enonceVocal = [
    `Bulletin de ${donnees.apprenant_nom ?? 'l’élève'}.`,
    donnees.periode_libelle ?? '',
    `Moyenne générale : ${formaterNote(donnees.moyenne_generale)} sur 20.`,
    donnees.rang ? `Rang : ${donnees.rang} sur ${donnees.effectif_classe ?? '—'}.` : '',
    donnees.mention ? `Mention ${donnees.mention}.` : '',
    donnees.appreciation_generale ?? '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <>
      <EntetePage
        fil={[{ libelle: 'Bulletins', href: '/bulletins' }, { libelle: donnees.numero }]}
        titre={donnees.apprenant_nom ?? 'Bulletin'}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span>{donnees.etablissement_nom}</span>
            <span aria-hidden>·</span>
            <span>{donnees.classe_libelle}</span>
            <span aria-hidden>·</span>
            <span>{donnees.periode_libelle}</span>
            {donnees.annee_libelle ? (
              <>
                <span aria-hidden>·</span>
                <span>{donnees.annee_libelle}</span>
              </>
            ) : null}
          </span>
        }
        actions={
          <>
            {lectureVocale ? (
              <Bouton
                variante="secondaire"
                onClick={() => lire(enonceVocal)}
                icone={<Volume2 size={17} aria-hidden />}
              >
                Écouter
              </Bouton>
            ) : null}
            <Bouton
              onClick={() => void api.ouvrir(`/bulletins/${parametres.id}/pdf`)}
              icone={<Printer size={17} aria-hidden />}
            >
              Imprimer le bulletin
            </Bouton>
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_20rem]">
        <Carte>
          <EnteteCarte
            titre="Résultats par matière"
            description="Moyennes pondérées par les coefficients de la série."
          />
          <Tableau
            legende="Notes par matière"
            lignes={donnees.lignes}
            cleLigne={(ligne) => ligne.matiere_id}
            colonnes={[
              {
                cle: 'matiere',
                entete: 'Matière',
                rendu: (ligne) => <span className="font-medium">{ligne.matiere_libelle}</span>,
              },
              {
                cle: 'moyenne',
                entete: 'Moyenne',
                alignement: 'droite',
                rendu: (ligne) => (
                  <span className="font-semibold tabular-nums">{formaterNote(ligne.moyenne)}</span>
                ),
              },
              {
                cle: 'coefficient',
                entete: 'Coef.',
                alignement: 'centre',
                rendu: (ligne) => ligne.coefficient,
              },
              {
                cle: 'points',
                entete: 'Points',
                alignement: 'droite',
                rendu: (ligne) => formaterNote(ligne.points),
              },
              {
                cle: 'rang',
                entete: 'Rang',
                alignement: 'droite',
                secondaire: true,
                rendu: (ligne) => ligne.rang ?? '—',
              },
              {
                cle: 'classe',
                entete: 'Moy. classe',
                alignement: 'droite',
                secondaire: true,
                rendu: (ligne) => formaterNote(ligne.moyenne_classe),
              },
              {
                cle: 'appreciation',
                entete: 'Appréciation',
                secondaire: true,
                rendu: (ligne) => ligne.appreciation ?? '—',
              },
            ]}
          />
          <div className="flex flex-wrap items-center justify-end gap-6 border-t px-5 py-4 text-sm">
            <span className="texte-doux">
              Total des points :{' '}
              <span className="font-semibold text-[rgb(var(--texte))] tabular-nums">
                {formaterNote(donnees.total_points)}
              </span>
            </span>
            <span className="texte-doux">
              Total des coefficients :{' '}
              <span className="font-semibold text-[rgb(var(--texte))] tabular-nums">
                {donnees.total_coefficients ?? '—'}
              </span>
            </span>
          </div>
        </Carte>

        <div className="space-y-4">
          <Carte>
            <CorpsCarte className="text-center">
              <p className="text-sm texte-doux">Moyenne générale</p>
              <p className="mt-1 text-5xl font-semibold tabular-nums tracking-tight">
                {formaterNote(donnees.moyenne_generale)}
              </p>
              <p className="text-sm texte-doux">sur 20</p>
              {donnees.mention ? (
                <div className="mt-3">
                  <Badge ton="succes" className="text-sm">
                    Mention {donnees.mention}
                  </Badge>
                </div>
              ) : null}
            </CorpsCarte>
          </Carte>

          <Carte>
            <EnteteCarte titre="Synthèse" />
            <CorpsCarte>
              <ListeDescriptive
                colonnes={1}
                entrees={[
                  {
                    terme: 'Rang',
                    valeur: donnees.rang
                      ? `${donnees.rang} sur ${donnees.effectif_classe ?? '—'}`
                      : '—',
                  },
                  { terme: 'Moyenne de la classe', valeur: formaterNote(donnees.moyenne_classe) },
                  { terme: 'Meilleure moyenne', valeur: formaterNote(donnees.moyenne_premier) },
                  {
                    terme: 'Moyenne la plus basse',
                    valeur: formaterNote(donnees.moyenne_dernier),
                  },
                  {
                    terme: 'Absences',
                    valeur: `${donnees.absences_heures} h dont ${donnees.absences_justifiees ?? 0} h justifiées`,
                  },
                  { terme: 'Retards', valeur: donnees.retards },
                  {
                    terme: 'Décision du conseil',
                    valeur: donnees.decision ? (
                      <Badge ton={tonDuStatut(donnees.decision)}>
                        {humaniser(donnees.decision)}
                      </Badge>
                    ) : (
                      '—'
                    ),
                  },
                  {
                    terme: 'Appréciation générale',
                    valeur: donnees.appreciation_generale ?? '—',
                  },
                ]}
              />
            </CorpsCarte>
          </Carte>

          {donnees.code_verification ? (
            <Carte>
              <CorpsCarte className="text-center">
                <p className="text-xs uppercase tracking-wide texte-doux">
                  Code de vérification
                </p>
                <p className="mt-1 break-all font-mono text-sm font-semibold">
                  {donnees.code_verification}
                </p>
                <p className="mt-2 text-xs texte-doux">
                  Ce bulletin est vérifiable en ligne à l&apos;aide de ce code.
                </p>
              </CorpsCarte>
            </Carte>
          ) : null}
        </div>
      </div>
    </>
  );
}
