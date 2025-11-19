package com.elecciones.backend.repository;

import com.elecciones.backend.model.VotoPresidencial;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;
import java.util.List;

public interface VotoPresidencialRepository extends JpaRepository<VotoPresidencial, UUID> {
    // Buscar todos los votos de un votante
    List<VotoPresidencial> findByVotanteId(UUID votanteId);

    // Buscar todos los votos de un candidato
    List<VotoPresidencial> findByCandidatoId(UUID candidatoId);

    // Buscar un voto específico por DNI del votante
    VotoPresidencial findByDniVotante(String dniVotante);
}
