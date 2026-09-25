'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Download, Paperclip, Upload, X } from 'lucide-react';
import { useRef, useState } from 'react';

import { Tableau } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Champ,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  Interrupteur,
  tonDuStatut,
} from '@/components/ui/primitives';
import { api, ErreurApi } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDateHeure, humaniser } from '@/lib/utils';

interface Document {
  id: string;
  reference: string;
  nom: string;
  nom_fichier: string;
  type_mime: string | null;
  taille_octets: number;
  version: number;
  statut: string;
  confidentiel: boolean;
  depose_le: string;
}

/** Taille lisible d'un fichier, au plus proche de l'unité qui lui convient. */
function formaterTaille(octets: number): string {
  if (octets < 1024) return `${octets} o`;
  if (octets < 1024 * 1024) return `${Math.round(octets / 1024)} Ko`;
  return `${(octets / (1024 * 1024)).toFixed(1)} Mo`;
}

/**
 * Pièces jointes d'une entité.
 *
 * Le moteur de documents est générique : le même panneau sert un établissement,
 * une session d'examen ou un dossier, en changeant simplement le type d'entité.
 */
export function DocumentsEntite({
  entiteType,
  entiteId,
  titre = 'Documents',
  description,
}: {
  entiteType: string;
  entiteId: string;
  titre?: string;
  description?: string;
}) {
  const fileAttente = useQueryClient();
  const { peut } = useSession();
  const champFichier = useRef<HTMLInputElement>(null);

  const [nom, setNom] = useState('');
  const [confidentiel, setConfidentiel] = useState(false);
  const [fichier, setFichier] = useState<File | null>(null);
  const [journal, setJournal] = useState<string | null>(null);

  const cle = ['documents-entite', entiteType, entiteId];

  const documents = useQuery({
    queryKey: cle,
    queryFn: () => api.get<Document[]>(`/documents/entite/${entiteType}/${entiteId}`),
  });

  function signaler(erreurBrute: unknown, defaut: string) {
    setJournal(erreurBrute instanceof ErreurApi ? erreurBrute.message : defaut);
  }

  const deposer = useMutation({
    mutationFn: () => {
      const charge = new FormData();
      charge.append('fichier', fichier!);
      charge.append('entite_type', entiteType);
      charge.append('entite_id', entiteId);
      charge.append('nom', nom.trim() || fichier!.name);
      charge.append('confidentiel', String(confidentiel));
      return api.post<Document>('/documents', charge);
    },
    onSuccess: (document) => {
      setJournal(`« ${document.nom} » déposé en version ${document.version}.`);
      setNom('');
      setFichier(null);
      setConfidentiel(false);
      if (champFichier.current) champFichier.current.value = '';
      void fileAttente.invalidateQueries({ queryKey: cle });
    },
    onError: (e) => signaler(e, "Le document n'a pas pu être déposé."),
  });

  const valider = useMutation({
    mutationFn: (variables: { document: Document; valide: boolean }) =>
      api.post<{ message: string }>(
        `/documents/${variables.document.id}/validation`,
        undefined,
        { parametres: { valide: variables.valide } },
      ),
    onSuccess: (reponse) => {
      setJournal(reponse.message);
      void fileAttente.invalidateQueries({ queryKey: cle });
    },
    onError: (e) => signaler(e, "Le document n'a pas pu être traité."),
  });

  const liste = documents.data ?? [];

  return (
    <Carte>
      <EnteteCarte
        titre={
          <span className="flex items-center gap-2">
            <Paperclip size={19} aria-hidden /> {titre}
          </span>
        }
        description={
          description ??
          'Pièces jointes conservées avec leur version, leur empreinte et leur état de validation.'
        }
        action={<Badge ton="neutre">{liste.length} document(s)</Badge>}
      />

      {documents.isLoading ? (
        <CorpsCarte>
          <Chargement libelle="Chargement des documents…" />
        </CorpsCarte>
      ) : (
        <Tableau
          legende="Documents rattachés"
          lignes={liste}
          cleLigne={(document) => document.id}
          vide={<EtatVide titre="Aucun document déposé" />}
          colonnes={[
            {
              cle: 'nom',
              entete: 'Document',
              rendu: (document) => (
                <span className="block max-w-[22rem]">
                  <span className="block truncate font-medium">{document.nom}</span>
                  <span className="block truncate font-mono text-xs texte-doux">
                    {document.reference} · v{document.version}
                  </span>
                </span>
              ),
            },
            {
              cle: 'fichier',
              entete: 'Fichier',
              secondaire: true,
              rendu: (document) => (
                <span className="min-w-0">
                  <span className="block truncate">{document.nom_fichier}</span>
                  <span className="block text-xs texte-doux">
                    {formaterTaille(document.taille_octets)}
                  </span>
                </span>
              ),
            },
            {
              cle: 'depot',
              entete: 'Déposé le',
              alignement: 'droite',
              secondaire: true,
              rendu: (document) => formaterDateHeure(document.depose_le),
            },
            {
              cle: 'statut',
              entete: 'État',
              rendu: (document) => (
                <span className="flex flex-wrap gap-1.5">
                  <Badge ton={tonDuStatut(document.statut)}>{humaniser(document.statut)}</Badge>
                  {document.confidentiel ? <Badge ton="alerte">Confidentiel</Badge> : null}
                </span>
              ),
            },
            {
              cle: 'actions',
              entete: 'Actions',
              alignement: 'droite',
              largeur: '18rem',
              rendu: (document) => (
                <span className="flex items-center justify-end gap-1.5">
                  <Bouton
                    taille="sm"
                    variante="fantome"
                    icone={<Download size={15} aria-hidden />}
                    onClick={() =>
                      void api
                        .telecharger(`/documents/${document.id}/telecharger`, document.nom_fichier)
                        .catch(() => setJournal('Le téléchargement a échoué.'))
                    }
                  >
                    Télécharger
                  </Bouton>
                  {peut('documents', 'VALIDATE') ? (
                    <>
                      <Bouton
                        taille="sm"
                        variante="fantome"
                        aria-label={`Valider ${document.nom}`}
                        disabled={valider.isPending}
                        onClick={() => valider.mutate({ document, valide: true })}
                        icone={<Check size={15} aria-hidden />}
                      />
                      <Bouton
                        taille="sm"
                        variante="fantome"
                        aria-label={`Rejeter ${document.nom}`}
                        disabled={valider.isPending}
                        onClick={() => valider.mutate({ document, valide: false })}
                        icone={<X size={15} aria-hidden />}
                      />
                    </>
                  ) : null}
                </span>
              ),
            },
          ]}
        />
      )}

      {peut('documents', 'CREATE') ? (
        <CorpsCarte className="border-t">
          <h3 className="mb-3 flex items-center gap-2 font-medium">
            <Upload size={17} aria-hidden /> Déposer un document
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <Champ
              etiquette="Intitulé"
              aide="À défaut, le nom du fichier est repris."
              value={nom}
              onChange={(evenement) => setNom(evenement.target.value)}
            />
            <div className="space-y-1.5">
              <label htmlFor={`fichier-${entiteId}`} className="block text-sm font-medium">
                Fichier
              </label>
              <input
                id={`fichier-${entiteId}`}
                ref={champFichier}
                type="file"
                onChange={(evenement) => setFichier(evenement.target.files?.[0] ?? null)}
                className="w-full rounded-lg border bg-[rgb(var(--fond-carte))] px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-[rgb(var(--fond-doux))] file:px-3 file:py-1.5 file:text-sm"
              />
            </div>
            <div className="flex items-end">
              <Interrupteur
                etiquette="Confidentiel"
                description="Réservé aux profils habilités."
                actif={confidentiel}
                onChange={() => setConfidentiel((precedent) => !precedent)}
              />
            </div>
          </div>
          <Bouton
            className="mt-3"
            disabled={!fichier}
            chargement={deposer.isPending}
            onClick={() => deposer.mutate()}
          >
            Déposer
          </Bouton>
          {journal ? (
            <p role="status" className="mt-2 text-sm texte-doux">
              {journal}
            </p>
          ) : null}
        </CorpsCarte>
      ) : null}
    </Carte>
  );
}
