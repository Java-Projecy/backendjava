package com.elecciones.backend.repository;

import com.elecciones.backend.model.Candidato;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;
import java.util.List;

public interface CandidatoRepository extends JpaRepository<Candidato, UUID> {
    // Buscar candidatos por tipo de elección
    List<Candidato> findByTipoEleccion(String tipoEleccion);

    // Buscar candidatos activos
    List<Candidato> findByIsActiveTrue();
}
