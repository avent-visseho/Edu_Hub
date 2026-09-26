'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CalendarCheck, CheckCircle2, Clock, UserX } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur, Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Champ,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
  Selection,
  tonDuStatut,
} from '@/components/ui/primitives';
import { api, ErreurApi } from '@/lib/api';
import { useSession } from '@/lib/session';
import { cn, formaterDate, formaterPourcentage, humaniser } from '@/lib/utils';

interface Classe {
  id: string;
  libelle: string;
  effectif: number;
}

interface Seance {
  id: string;
  date_seance: string;
  heure_debut: string;
  heure_fin: string;
  matiere_libelle: string | null;
  enseignant_nom: string | null;
  statut: string;
  appel_fait: boolean;
  contenu_seance: string | null;
  saisies: number;
  presents: number;
  absents: number;
  retards: number;
}

interface Apprenant {
  id: string;
  identifiant_educatif: string;
  nom_complet: string;
  tiers_temps: boolean;
  statut: string;
}

interface Presence {
  id: string;
  seance_id: string;
  apprenant_id: string;
  statut: string;
  minutes_retard: number;
  justification: string | null;
  nom_complet: string | null;
  identifiant_educatif: string | null;
}

/** Statuts de présence reconnus par le moteur d'assiduité. */
const STATUTS = [
  { valeur: 'PRESENT', libelle: 'Présent' },
  { valeur: 'RETARD', libelle: 'En retard' },
  { valeur: 'ABSENCE_JUSTIFIEE', libelle: 'Absence justifiée' },
  { valeur: 'ABSENCE_INJUSTIFIEE', libelle: 'Absence injustifiée' },
  { valeur: 'ABSENT', libelle: 'Absent (à qualifier)' },
  { valeur: 'EXCLU_COURS', libelle: 'Exclu du cours' },
];

interface Ligne {
  statut: string;
  minutes_retard: number;
  justification: string;
}

export default function PageAppelClasse() {
  const parametres = useParams<{ id: string }>();
  const fileAttente = useQueryClient();
  const { peut } = useSession();

  const [seanceId, setSeanceId] = useState('');
  const [lignes, setLignes] = useState<Record<string, Ligne>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const classe = useQuery({
    queryKey: ['classe', parametres.id],
    queryFn: () => api.get<Classe>(`/classes/${parametres.id}`),
  });

  const seances = useQuery({
    queryKey: ['seances-classe', parametres.id],
    queryFn: () => api.get<Seance[]>(`/classes/${parametres.id}/seances`, { limite: 60 }),
  });

  const effectif = useQuery({
    queryKey: ['effectif-classe', parametres.id],
    queryFn: () => api.get<Apprenant[]>(`/classes/${parametres.id}/apprenants`),
  });

  const presences = useQuery({
    queryKey: ['presences-seance', seanceId],
    queryFn: () => api.get<Presence[]>(`/seances/${seanceId}/presences`),
    enabled: Boolean(seanceId),
  });

  // Première séance sans appel : c'est celle que l'enseignant vient traiter.
  useEffect(() => {
    if (seanceId || !seances.data?.length) return;
    const aTraiter = seances.data.find((seance) => !seance.appel_fait) ?? seances.data[0];
    setSeanceId(aTraiter.id);
  }, [seances.data, seanceId]);

  // La saisie repart des présences déjà enregistrées, complétées par « Présent ».
  useEffect(() => {
    if (!effectif.data) return;
    const deja = new Map(
      (presences.data ?? []).map((presence) => [presence.apprenant_id, presence]),
    );
    const initiales: Record<string, Ligne> = {};
    for (const apprenant of effectif.data) {
      const presence = deja.get(apprenant.id);
      initiales[apprenant.id] = {
        statut: presence?.statut ?? 'PRESENT',
        minutes_retard: presence?.minutes_retard ?? 0,
        justification: presence?.justification ?? '',
      };
    }
    setLignes(initiales);
  }, [effectif.data, presences.data, seanceId]);

  const seance = useMemo(
    () => seances.data?.find((element) => element.id === seanceId) ?? null,
    [seances.data, seanceId],
  );

  const enregistrer = useMutation({
    mutationFn: () =>
      api.post<{ message: string }>(`/seances/${seanceId}/appel`, {
        lignes: Object.entries(lignes).map(([apprenantId, ligne]) => ({
          apprenant_id: apprenantId,
          statut: ligne.statut,
          minutes_retard: ligne.statut === 'RETARD' ? ligne.minutes_retard : 0,
          justification: ligne.justification || null,
        })),
      }),
    onSuccess: (reponse) => {
      setErreur(null);
      setMessage(reponse.message);
      void fileAttente.invalidateQueries({ queryKey: ['seances-classe', parametres.id] });
      void fileAttente.invalidateQueries({ queryKey: ['presences-seance', seanceId] });
      void fileAttente.invalidateQueries({ queryKey: ['assiduite-classe', parametres.id] });
    },
    onError: (erreurBrute: unknown) => {
      setMessage(null);
      setErreur(
        erreurBrute instanceof ErreurApi
          ? erreurBrute.message
          : "L'appel n'a pas pu être enregistré.",
      );
    },
  });

  function modifier(apprenantId: string, champs: Partial<Ligne>) {
    setLignes((precedent) => ({
      ...precedent,
      [apprenantId]: { ...precedent[apprenantId], ...champs },
    }));
  }

  if (classe.isLoading) return <Chargement libelle="Ouverture de la classe…" />;
  if (classe.isError) return <MessageErreur erreur={classe.error} />;

  const apprenants = effectif.data ?? [];
  const valeurs = Object.values(lignes);
  const presents = valeurs.filter((ligne) => ligne.statut === 'PRESENT').length;
  const retards = valeurs.filter((ligne) => ligne.statut === 'RETARD').length;
  const absents = valeurs.filter((ligne) => ligne.statut.startsWith('AB')).length;
  const autorise = peut('presences', 'CREATE');

  return (
    <>
      <EntetePage
        fil={[
          { libelle: 'Classes', href: '/classes' },
          { libelle: classe.data!.libelle, href: `/classes/${parametres.id}` },
          { libelle: 'Appel' },
        ]}
        titre={`Appel — ${classe.data!.libelle}`}
        description="Saisie des présences séance par séance. Chaque enregistrement met à jour la synthèse d'assiduité."
        actions={
          <Bouton
            disabled={!autorise || !seanceId || apprenants.length === 0}
            chargement={enregistrer.isPending}
            icone={<CheckCircle2 size={17} aria-hidden />}
            onClick={() => enregistrer.mutate()}
          >
            Enregistrer l&apos;appel
          </Bouton>
        }
      />

      {message ? (
        <p
          role="status"
          className="mb-4 rounded-lg border border-[rgb(var(--succes))]/40 bg-[rgb(var(--succes))]/10 px-4 py-3 text-sm"
        >
          {message}
        </p>
      ) : null}
      {erreur ? (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-[rgb(var(--danger))]/40 bg-[rgb(var(--danger))]/10 px-4 py-3 text-sm"
        >
          {erreur}
        </p>
      ) : null}

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur
          libelle="Effectif appelé"
          valeur={apprenants.length}
          icone={<CalendarCheck size={19} aria-hidden />}
          pictogramme="👥"
        />
        <Indicateur
          libelle="Présents"
          valeur={presents}
          unite={formaterPourcentage(
            apprenants.length > 0 ? (presents / apprenants.length) * 100 : 0,
          )}
          icone={<CheckCircle2 size={19} aria-hidden />}
          pictogramme="✅"
        />
        <Indicateur
          libelle="Absents"
          valeur={absents}
          icone={<UserX size={19} aria-hidden />}
          pictogramme="❌"
        />
        <Indicateur
          libelle="Retards"
          valeur={retards}
          icone={<Clock size={19} aria-hidden />}
          pictogramme="⏰"
        />
      </div>

      <Carte className="mb-4">
        <EnteteCarte
          titre="Séance à traiter"
          description="Les séances sans appel apparaissent en tête de liste."
        />
        <CorpsCarte>
          {seances.isLoading ? (
            <Chargement libelle="Chargement des séances…" />
          ) : seances.data?.length ? (
            <div className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
              <Selection
                etiquette="Séance"
                value={seanceId}
                onChange={(evenement) => setSeanceId(evenement.target.value)}
                options={seances.data.map((element) => ({
                  valeur: element.id,
                  libelle: `${formaterDate(element.date_seance)} · ${element.heure_debut} · ${
                    element.matiere_libelle ?? 'Matière non précisée'
                  }${element.appel_fait ? '' : ' — appel à faire'}`,
                }))}
              />
              {seance ? (
                <div className="space-y-1.5 text-sm">
                  <p className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">
                      {seance.matiere_libelle ?? 'Matière non précisée'}
                    </span>
                    <Badge ton={tonDuStatut(seance.statut)}>{humaniser(seance.statut)}</Badge>
                    <Badge ton={seance.appel_fait ? 'succes' : 'alerte'}>
                      {seance.appel_fait ? 'Appel effectué' : 'Appel à faire'}
                    </Badge>
                  </p>
                  <p className="texte-doux">
                    {formaterDate(seance.date_seance)} de {seance.heure_debut} à {seance.heure_fin}
                    {seance.enseignant_nom ? ` · ${seance.enseignant_nom}` : ''}
                  </p>
                  {seance.contenu_seance ? (
                    <p className="texte-doux">{seance.contenu_seance}</p>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : (
            <EtatVide
              titre="Aucune séance programmée"
              description="Programmez une séance depuis un créneau de l'emploi du temps pour pouvoir faire l'appel."
            />
          )}
        </CorpsCarte>
      </Carte>

      <Carte>
        <EnteteCarte
          titre="Feuille d'appel"
          description={
            autorise
              ? 'Tous les apprenants sont présents par défaut ; ne modifiez que les exceptions.'
              : "Votre profil ne permet pas de saisir l'appel."
          }
        />
        {effectif.isLoading ? (
          <CorpsCarte>
            <Chargement libelle="Chargement de l'effectif…" />
          </CorpsCarte>
        ) : (
          <Tableau
            legende={`Feuille d'appel de la classe ${classe.data!.libelle}`}
            lignes={apprenants}
            cleLigne={(apprenant) => apprenant.id}
            vide={<EtatVide titre="Aucun apprenant inscrit dans cette classe" />}
            colonnes={[
              {
                cle: 'apprenant',
                entete: 'Apprenant',
                rendu: (apprenant) => (
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{apprenant.nom_complet}</span>
                    <span className="block font-mono text-xs texte-doux">
                      {apprenant.identifiant_educatif}
                    </span>
                  </span>
                ),
              },
              {
                cle: 'statut',
                entete: 'Présence',
                largeur: '22%',
                rendu: (apprenant) => (
                  <Selection
                    etiquette={`Présence de ${apprenant.nom_complet}`}
                    etiquetteMasquee
                    disabled={!autorise}
                    options={STATUTS}
                    value={lignes[apprenant.id]?.statut ?? 'PRESENT'}
                    onChange={(evenement) =>
                      modifier(apprenant.id, { statut: evenement.target.value })
                    }
                  />
                ),
              },
              {
                cle: 'retard',
                entete: 'Retard (min)',
                alignement: 'droite',
                largeur: '12%',
                rendu: (apprenant) => (
                  <Champ
                    etiquette={`Minutes de retard de ${apprenant.nom_complet}`}
                    etiquetteMasquee
                    type="number"
                    min={0}
                    max={240}
                    disabled={!autorise || lignes[apprenant.id]?.statut !== 'RETARD'}
                    value={lignes[apprenant.id]?.minutes_retard ?? 0}
                    onChange={(evenement) =>
                      modifier(apprenant.id, {
                        minutes_retard: Number(evenement.target.value) || 0,
                      })
                    }
                    className={cn(
                      'text-right',
                      lignes[apprenant.id]?.statut !== 'RETARD' && 'opacity-50',
                    )}
                  />
                ),
              },
              {
                cle: 'justification',
                entete: 'Justification',
                secondaire: true,
                rendu: (apprenant) => (
                  <Champ
                    etiquette={`Justification pour ${apprenant.nom_complet}`}
                    etiquetteMasquee
                    disabled={!autorise}
                    placeholder="Motif communiqué…"
                    value={lignes[apprenant.id]?.justification ?? ''}
                    onChange={(evenement) =>
                      modifier(apprenant.id, { justification: evenement.target.value })
                    }
                  />
                ),
              },
            ]}
          />
        )}
      </Carte>
    </>
  );
}
