package com.elecciones.backend.repository;

import com.elecciones.backend.model.VotoDistrital;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;
import java.util.List;

public interface VotoDistritalRepository extends JpaRepository<VotoDistrital, UUID> {
    // Buscar todos los votos de un votante
    List<VotoDistrital> findByVotanteId(UUID votanteId);

    // Buscar todos los votos de un candidato
    List<VotoDistrital> findByCandidatoId(UUID candidatoId);

    // Buscar un voto específico por DNI del votante
    VotoDistrital findByDniVotante(String dniVotante);
}
