package com.elecciones.backend.model;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "votos_distritales")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class VotoDistrital {

    @Id
    @GeneratedValue
    private UUID id;

    @ManyToOne
    @JoinColumn(name = "votante_id", nullable = false)
    private Votante votante;

    @ManyToOne
    @JoinColumn(name = "candidato_id", nullable = false)
    private Candidato candidato;

    @Column(name = "dni_votante", nullable = false)
    private String dniVotante;

    @Builder.Default
    private LocalDateTime fecha_voto = LocalDateTime.now();

    private String departamento;
    private String provincia;
    private String distrito;
}
