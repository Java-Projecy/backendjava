package com.elecciones.backend.repository;

import com.elecciones.backend.model.VotoRegional;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;
import java.util.List;

public interface VotoRegionalRepository extends JpaRepository<VotoRegional, UUID> {
    // Buscar todos los votos de un votante
    List<VotoRegional> findByVotanteId(UUID votanteId);

    // Buscar todos los votos de un candidato
    List<VotoRegional> findByCandidatoId(UUID candidatoId);

    // Buscar un voto específico por DNI del votante
    VotoRegional findByDniVotante(String dniVotante);
}
