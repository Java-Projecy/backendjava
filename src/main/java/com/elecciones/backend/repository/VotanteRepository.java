package com.elecciones.backend.repository;

import com.elecciones.backend.model.Votante;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface VotanteRepository extends JpaRepository<Votante, UUID> {
    Votante findByDni(String dni);
}
